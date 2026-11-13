from collections import deque
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from io import BytesIO
from typing import Optional

import openpyxl
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from openpyxl.styles import Alignment, Font
from pydantic import BaseModel, Field
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app import models
from app.database import get_db
from app.dependencies.auth_dependency import get_current_user

router = APIRouter(prefix="/buyer-ledger", tags=["Buyer Ledger"])
LEDGER_START_DATE = date(2026, 7, 1)


class ReceiptCreate(BaseModel):
    received_date: date
    amount: Decimal = Field(
        gt=Decimal("0"),
        max_digits=18,
        decimal_places=2,
    )
    payment_method: Optional[str] = Field(default=None, max_length=50)
    reference_number: Optional[str] = Field(default=None, max_length=150)
    notes: Optional[str] = Field(default=None, max_length=2000)


class OpeningBalanceUpdate(BaseModel):
    opening_balance: Decimal = Field(max_digits=18, decimal_places=2)


def _validate_ledger_dates(
    from_date: Optional[date],
    to_date: Optional[date],
) -> None:
    if from_date and from_date < LEDGER_START_DATE:
        raise HTTPException(
            status_code=422,
            detail="Buyer ledger starts on 2026-07-01 (FY 2026-2027)",
        )
    if to_date and to_date < LEDGER_START_DATE:
        raise HTTPException(
            status_code=422,
            detail="Buyer ledger starts on 2026-07-01 (FY 2026-2027)",
        )
    if from_date and to_date and from_date > to_date:
        raise HTTPException(
            status_code=422,
            detail="From date must be on or before to date",
        )


def _client_owned_by_user(
    db: Session,
    client_id: int,
    user_id: int,
) -> bool:
    return (
        db.query(models.Client.id)
        .filter(
            models.Client.id == client_id,
            models.Client.user_id == user_id,
        )
        .first()
        is not None
    )


def _owned_buyer(
    db: Session,
    buyer_id: int,
    client_id: int,
    user_id: int,
) -> models.Buyer:
    buyer = (
        db.query(models.Buyer)
        .join(models.Client, models.Buyer.client_id == models.Client.id)
        .filter(
            models.Buyer.id == buyer_id,
            models.Buyer.client_id == client_id,
            models.Client.user_id == user_id,
        )
        .first()
    )
    if not buyer:
        raise HTTPException(status_code=404, detail="Buyer not found")
    return buyer


def _invoice_rows(
    db: Session,
    client_id: int,
    buyer_id: int,
    before: Optional[datetime] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
):
    query = (
        db.query(
            models.Invoice,
            func.coalesce(func.sum(models.InvoiceItem.totalValues), 0).label("amount"),
        )
        .outerjoin(
            models.InvoiceItem,
            models.InvoiceItem.invoice_id == models.Invoice.id,
        )
        .filter(
            models.Invoice.client_id == client_id,
            models.Invoice.buyer_id == buyer_id,
            models.Invoice.status == "posted",
            models.Invoice.invoiceType.in_(("Sale Invoice", "Debit Note")),
            models.Invoice.invoiceDate
            >= datetime.combine(LEDGER_START_DATE, time.min),
        )
        .group_by(models.Invoice.id)
    )
    if before is not None:
        query = query.filter(models.Invoice.invoiceDate < before)
    else:
        if from_date:
            query = query.filter(
                models.Invoice.invoiceDate >= datetime.combine(from_date, time.min)
            )
        if to_date:
            query = query.filter(
                models.Invoice.invoiceDate
                < datetime.combine(to_date + timedelta(days=1), time.min)
            )
    return query.order_by(
        models.Invoice.invoiceDate.asc(),
        models.Invoice.id.asc(),
    ).all()


def _signed_amount(
    invoice: models.Invoice,
    amount,
) -> tuple[Decimal, Decimal, Decimal]:
    value = Decimal(str(amount or 0))
    if invoice.invoiceType == "Sale Invoice":
        return value, Decimal("0"), value
    return Decimal("0"), value, -value


def _receipt_rows(
    db: Session,
    client_id: int,
    buyer_id: int,
    before: Optional[date] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
):
    query = db.query(models.BuyerReceipt).filter(
        models.BuyerReceipt.client_id == client_id,
        models.BuyerReceipt.buyer_id == buyer_id,
        models.BuyerReceipt.received_date >= LEDGER_START_DATE,
    )
    if before is not None:
        query = query.filter(models.BuyerReceipt.received_date < before)
    else:
        if from_date:
            query = query.filter(models.BuyerReceipt.received_date >= from_date)
        if to_date:
            query = query.filter(models.BuyerReceipt.received_date <= to_date)
    return query.order_by(
        models.BuyerReceipt.received_date.asc(),
        models.BuyerReceipt.id.asc(),
    ).all()


def _ledger_data(
    db: Session,
    client_id: int,
    buyer_id: int,
    from_date: Optional[date],
    to_date: Optional[date],
    base_opening_balance: Decimal,
) -> dict:
    opening_balance = Decimal(str(base_opening_balance or 0))
    if from_date and from_date > LEDGER_START_DATE:
        opening_rows = _invoice_rows(
            db,
            client_id,
            buyer_id,
            before=datetime.combine(from_date, time.min),
        )
        opening_balance += sum(
            _signed_amount(invoice, amount)[2]
            for invoice, amount in opening_rows
        ) - sum(
            (receipt.amount for receipt in _receipt_rows(
                db,
                client_id,
                buyer_id,
                before=from_date,
            )),
            Decimal("0"),
        )

    transactions = _invoice_rows(
        db,
        client_id,
        buyer_id,
        from_date=from_date,
        to_date=to_date,
    )
    receipts = _receipt_rows(
        db,
        client_id,
        buyer_id,
        from_date=from_date,
        to_date=to_date,
    )
    events = []
    for invoice, amount in transactions:
        events.append(
            (
                invoice.invoiceDate.date().isoformat(),
                0,
                invoice.id,
                "invoice",
                invoice,
                amount,
            )
        )
    for receipt in receipts:
            events.append(
                (
                    receipt.received_date.isoformat(),
                    1,
                    receipt.id,
                    "receipt",
                    receipt,
                    receipt.amount,
                )
            )
    events.sort(key=lambda event: event[:3])

    balance = opening_balance
    rows = []
    for _, _, _, event_type, record, amount in events:
        if event_type == "invoice":
            debit, credit, signed_amount = _signed_amount(record, amount)
            row = {
                "invoice_id": record.id,
                "receipt_id": None,
                "date": record.invoiceDate.date().isoformat(),
                "invoice_type": record.invoiceType,
                "invoice_number": record.internal_invoice_no,
                "fbr_invoice_number": record.fbrInvoiceNo,
                "reference_number": record.invoiceRefNo,
                "payment_method": None,
                "notes": None,
                "debit": float(debit),
                "credit": float(credit),
            }
        else:
            signed_amount = -Decimal(str(amount or 0))
            row = {
                "invoice_id": None,
                "receipt_id": record.id,
                "date": record.received_date.isoformat(),
                "invoice_type": "Receipt",
                "invoice_number": None,
                "fbr_invoice_number": None,
                "reference_number": record.reference_number,
                "payment_method": record.payment_method,
                "notes": record.notes,
                "debit": 0.0,
                "credit": float(amount or 0),
            }
        balance += signed_amount
        row["balance"] = float(balance)
        rows.append(row)

    return {
        "opening_balance": float(opening_balance),
        "closing_balance": float(balance),
        "transactions": rows,
    }


def _rebuild_receipt_allocations(
    db: Session,
    client_id: int,
    buyer_id: int,
) -> None:
    invoices = _invoice_rows(db, client_id, buyer_id)
    receipts = _receipt_rows(db, client_id, buyer_id)
    events = [
        (
            invoice.invoiceDate.date(),
            0,
            invoice.id,
            "invoice",
            invoice,
            Decimal(str(amount or 0)),
        )
        for invoice, amount in invoices
    ]
    events.extend(
        (
            receipt.received_date,
            1,
            receipt.id,
            "receipt",
            receipt,
            Decimal(str(receipt.amount or 0)),
        )
        for receipt in receipts
    )
    events.sort(key=lambda event: event[:3])

    outstanding_invoices = deque()
    available_credits = deque()
    allocations = []

    def apply_credits() -> None:
        while outstanding_invoices and available_credits:
            invoice_id, outstanding = outstanding_invoices[0]
            receipt_id, available = available_credits[0]
            applied = min(outstanding, available)
            if receipt_id is not None:
                allocations.append((receipt_id, invoice_id, applied))
            outstanding -= applied
            available -= applied
            if outstanding == 0:
                outstanding_invoices.popleft()
            else:
                outstanding_invoices[0][1] = outstanding
            if available == 0:
                available_credits.popleft()
            else:
                available_credits[0][1] = available

    for _, _, _, event_type, record, amount in events:
        if event_type == "invoice" and record.invoiceType == "Sale Invoice":
            outstanding_invoices.append([record.id, amount])
        else:
            source_receipt_id = record.id if event_type == "receipt" else None
            available_credits.append([source_receipt_id, amount])
        apply_credits()

    for receipt_id, unapplied_amount in available_credits:
        if receipt_id is not None and unapplied_amount > 0:
            allocations.append((receipt_id, None, unapplied_amount))

    receipt_ids = [receipt.id for receipt in receipts]
    if receipt_ids:
        db.query(models.BuyerReceiptAllocation).filter(
            models.BuyerReceiptAllocation.receipt_id.in_(receipt_ids)
        ).delete(synchronize_session=False)
    db.add_all(
        models.BuyerReceiptAllocation(
            receipt_id=receipt_id,
            invoice_id=invoice_id,
            amount=amount,
        )
        for receipt_id, invoice_id, amount in allocations
    )


@router.get("/buyers")
def list_ledger_buyers(
    client_id: int,
    search: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    if not _client_owned_by_user(db, client_id, current_user["id"]):
        raise HTTPException(status_code=404, detail="Client not found")

    query = db.query(models.Buyer).filter(
        models.Buyer.client_id == client_id
    )
    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                models.Buyer.name.ilike(term),
                models.Buyer.ntn_cnic.ilike(term),
            )
        )
    total = query.count()
    buyers = query.order_by(models.Buyer.name.asc()).offset(skip).limit(limit).all()
    return {
        "items": [
            {
                "id": buyer.id,
                "name": buyer.name,
                "ntn_cnic": buyer.ntn_cnic,
                "opening_balance": float(buyer.opening_balance),
            }
            for buyer in buyers
        ],
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.post("/{buyer_id}/receipts")
def create_buyer_receipt(
    buyer_id: int,
    payload: ReceiptCreate,
    client_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    if payload.received_date < LEDGER_START_DATE:
        raise HTTPException(
            status_code=422,
            detail="Buyer receipts can be recorded from 2026-07-01 (FY 2026-2027)",
        )
    _owned_buyer(db, buyer_id, client_id, current_user["id"])
    buyer = (
        db.query(models.Buyer)
        .filter(
            models.Buyer.id == buyer_id,
            models.Buyer.client_id == client_id,
        )
        .with_for_update()
        .first()
    )
    if not buyer:
        raise HTTPException(status_code=404, detail="Buyer not found")

    receipt = models.BuyerReceipt(
        client_id=client_id,
        buyer_id=buyer_id,
        received_date=payload.received_date,
        amount=payload.amount,
        payment_method=payload.payment_method.strip() if payload.payment_method else None,
        reference_number=(
            payload.reference_number.strip()
            if payload.reference_number
            else None
        ),
        notes=payload.notes.strip() if payload.notes else None,
        created_by=current_user["id"],
    )
    db.add(receipt)
    db.flush()
    _rebuild_receipt_allocations(db, client_id, buyer_id)
    db.flush()
    allocated_amount = (
        db.query(func.coalesce(func.sum(models.BuyerReceiptAllocation.amount), 0))
        .filter(
            models.BuyerReceiptAllocation.receipt_id == receipt.id,
            models.BuyerReceiptAllocation.invoice_id.is_not(None),
        )
        .scalar()
    )
    unapplied_amount = payload.amount - Decimal(str(allocated_amount or 0))
    db.commit()
    return {
        "id": receipt.id,
        "buyer_id": buyer_id,
        "received_date": receipt.received_date.isoformat(),
        "amount": float(receipt.amount),
        "allocated_amount": float(allocated_amount or 0),
        "unapplied_amount": float(unapplied_amount),
    }


@router.put("/{buyer_id}/receipts/{receipt_id}")
def update_buyer_receipt(
    buyer_id: int,
    receipt_id: int,
    payload: ReceiptCreate,
    client_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    if payload.received_date < LEDGER_START_DATE:
        raise HTTPException(
            status_code=422,
            detail="Buyer receipts can be recorded from 2026-07-01 (FY 2026-2027)",
        )
    _owned_buyer(db, buyer_id, client_id, current_user["id"])
    buyer = (
        db.query(models.Buyer)
        .filter(
            models.Buyer.id == buyer_id,
            models.Buyer.client_id == client_id,
        )
        .with_for_update()
        .first()
    )
    receipt = (
        db.query(models.BuyerReceipt)
        .filter(
            models.BuyerReceipt.id == receipt_id,
            models.BuyerReceipt.client_id == client_id,
            models.BuyerReceipt.buyer_id == buyer_id,
        )
        .with_for_update()
        .first()
    )
    if not buyer or not receipt:
        raise HTTPException(status_code=404, detail="Buyer receipt not found")

    receipt.received_date = payload.received_date
    receipt.amount = payload.amount
    receipt.payment_method = payload.payment_method.strip() if payload.payment_method else None
    receipt.reference_number = (
        payload.reference_number.strip()
        if payload.reference_number
        else None
    )
    receipt.notes = payload.notes.strip() if payload.notes else None
    _rebuild_receipt_allocations(db, client_id, buyer_id)
    db.commit()
    return {
        "id": receipt.id,
        "buyer_id": buyer_id,
        "received_date": receipt.received_date.isoformat(),
        "amount": float(receipt.amount),
    }


@router.delete("/{buyer_id}/receipts/{receipt_id}")
def delete_buyer_receipt(
    buyer_id: int,
    receipt_id: int,
    client_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    _owned_buyer(db, buyer_id, client_id, current_user["id"])
    buyer = (
        db.query(models.Buyer)
        .filter(
            models.Buyer.id == buyer_id,
            models.Buyer.client_id == client_id,
        )
        .with_for_update()
        .first()
    )
    receipt = (
        db.query(models.BuyerReceipt)
        .filter(
            models.BuyerReceipt.id == receipt_id,
            models.BuyerReceipt.client_id == client_id,
            models.BuyerReceipt.buyer_id == buyer_id,
        )
        .with_for_update()
        .first()
    )
    if not buyer or not receipt:
        raise HTTPException(status_code=404, detail="Buyer receipt not found")

    db.delete(receipt)
    db.flush()
    _rebuild_receipt_allocations(db, client_id, buyer_id)
    db.commit()
    return {"deleted": True, "receipt_id": receipt_id}


@router.get("/{buyer_id}")
def get_buyer_ledger(
    buyer_id: int,
    client_id: int,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    _validate_ledger_dates(from_date, to_date)
    buyer = _owned_buyer(db, buyer_id, client_id, current_user["id"])
    return {
        "buyer": {
            "id": buyer.id,
            "name": buyer.name,
            "ntn_cnic": buyer.ntn_cnic,
            "opening_balance": float(buyer.opening_balance),
        },
        **_ledger_data(
            db,
            client_id,
            buyer_id,
            from_date,
            to_date,
            Decimal(str(buyer.opening_balance or 0)),
        ),
    }


@router.put("/{buyer_id}/opening-balance")
def update_buyer_opening_balance(
    buyer_id: int,
    payload: OpeningBalanceUpdate,
    client_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    buyer = _owned_buyer(db, buyer_id, client_id, current_user["id"])
    buyer.opening_balance = payload.opening_balance
    db.commit()
    db.refresh(buyer)
    return {
        "buyer_id": buyer.id,
        "opening_balance": float(buyer.opening_balance),
    }


@router.get("/{buyer_id}/export/excel")
def export_buyer_ledger(
    buyer_id: int,
    client_id: int,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    _validate_ledger_dates(from_date, to_date)
    buyer = _owned_buyer(db, buyer_id, client_id, current_user["id"])
    ledger = _ledger_data(
        db,
        client_id,
        buyer_id,
        from_date,
        to_date,
        Decimal(str(buyer.opening_balance or 0)),
    )

    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Buyer Ledger"
    sheet.append(["Buyer", buyer.name])
    sheet.append(["NTN/CNIC", buyer.ntn_cnic])
    sheet.append(
        [
            "Period",
            f"{from_date.isoformat() if from_date else 'Beginning'} to "
            f"{to_date.isoformat() if to_date else 'Current'}",
        ]
    )
    sheet.append([])
    sheet.append(
        [
            "Date",
            "Transaction",
            "System Invoice No.",
            "Reference No.",
            "Payment Method",
            "Notes",
            "Debit",
            "Credit",
            "Balance",
        ]
    )
    for cell in sheet[5]:
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal="center")

    start_date = from_date.isoformat() if from_date else "Beginning"
    sheet.append(
        [
            start_date,
            "Opening Balance",
            None,
            None,
            None,
            None,
            None,
            None,
            ledger["opening_balance"],
        ]
    )
    for row in ledger["transactions"]:
        sheet.append(
            [
                row["date"],
                row["invoice_type"],
                row["invoice_number"],
                row["reference_number"],
                row["payment_method"],
                row["notes"],
                row["debit"],
                row["credit"],
                row["balance"],
            ]
        )
    sheet.append(
        [
            None,
            "Totals",
            None,
            None,
            None,
            None,
            sum(row["debit"] for row in ledger["transactions"]),
            sum(row["credit"] for row in ledger["transactions"]),
            None,
        ]
    )
    for cell in sheet[sheet.max_row]:
        cell.font = Font(bold=True)

    end_date = to_date.isoformat() if to_date else "Current"
    sheet.append(
        [
            end_date,
            "Closing Balance",
            None,
            None,
            None,
            None,
            None,
            None,
            ledger["closing_balance"],
        ]
    )

    for row in sheet.iter_rows(min_row=6, min_col=7, max_col=9):
        for cell in row:
            cell.number_format = '#,##0.00;[Red]-#,##0.00'
    for column_cells in sheet.columns:
        max_length = max(
            (len(str(cell.value)) for cell in column_cells if cell.value is not None),
            default=0,
        )
        sheet.column_dimensions[column_cells[0].column_letter].width = min(max_length + 3, 40)

    buffer = BytesIO()
    workbook.save(buffer)
    buffer.seek(0)
    filename = f"Buyer_Ledger_{buyer.id}.xlsx"
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
