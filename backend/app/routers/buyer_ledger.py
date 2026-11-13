from collections import deque
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from io import BytesIO
from typing import Optional

import openpyxl
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from pydantic import BaseModel, Field
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    LongTable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from sqlalchemy import func, or_
from sqlalchemy.orm import Session
from xml.sax.saxutils import escape

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


def _buyer_ledger_export_data(
    buyer_id: int,
    client_id: int,
    from_date: Optional[date],
    to_date: Optional[date],
    db: Session,
    user_id: int,
):
    _validate_ledger_dates(from_date, to_date)
    buyer = _owned_buyer(db, buyer_id, client_id, user_id)
    ledger = _ledger_data(
        db,
        client_id,
        buyer_id,
        from_date,
        to_date,
        Decimal(str(buyer.opening_balance or 0)),
    )
    return buyer, ledger


@router.get("/{buyer_id}/export/excel")
def export_buyer_ledger(
    buyer_id: int,
    client_id: int,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    buyer, ledger = _buyer_ledger_export_data(
        buyer_id,
        client_id,
        from_date,
        to_date,
        db,
        current_user["id"],
    )

    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Buyer Ledger"
    sheet.sheet_view.showGridLines = False

    navy_fill = PatternFill("solid", fgColor="17324D")
    blue_fill = PatternFill("solid", fgColor="2563EB")
    pale_fill = PatternFill("solid", fgColor="EEF5FC")
    stripe_fill = PatternFill("solid", fgColor="F7FAFD")
    white_font = Font(name="Aptos", color="FFFFFF", bold=True)
    title_font = Font(name="Aptos Display", size=18, bold=True, color="FFFFFF")
    muted_font = Font(name="Aptos", size=10, color="64748B")
    border_bottom = Border(
        bottom=Side(style="hair", color="DCE5EF")
    )

    sheet.merge_cells("A1:I1")
    sheet["A1"] = "BUYER LEDGER"
    sheet["A1"].font = title_font
    sheet["A1"].alignment = Alignment(vertical="center")
    for cell in sheet[1]:
        cell.fill = navy_fill
    sheet.row_dimensions[1].height = 34

    sheet.merge_cells("A2:I2")
    sheet["A2"] = "ACCOUNT STATEMENT"
    sheet["A2"].font = Font(name="Aptos", size=10, color="D8E8F7")
    sheet["A2"].alignment = Alignment(vertical="center")
    for cell in sheet[2]:
        cell.fill = navy_fill
    sheet.row_dimensions[2].height = 22

    period = (
        f"{from_date.isoformat() if from_date else 'Beginning'} to "
        f"{to_date.isoformat() if to_date else 'Current'}"
    )
    generated_at = datetime.now().strftime("%d %b %Y, %H:%M")
    for row, label, value, second_label, second_value in (
        (4, "BUYER", buyer.name, "NTN/CNIC", buyer.ntn_cnic or "-"),
        (5, "PERIOD", period, "GENERATED", generated_at),
    ):
        sheet.cell(row, 1, label)
        sheet.merge_cells(start_row=row, start_column=2, end_row=row, end_column=4)
        sheet.cell(row, 2, value)
        sheet.cell(row, 5, second_label)
        sheet.merge_cells(start_row=row, start_column=6, end_row=row, end_column=9)
        sheet.cell(row, 6, second_value)
        for column in (1, 5):
            sheet.cell(row, column).font = Font(
                name="Aptos", size=9, bold=True, color="64748B"
            )
        for column in (2, 6):
            sheet.cell(row, column).font = Font(
                name="Aptos", size=10, color="17324D"
            )
        sheet.row_dimensions[row].height = 22

    summary_items = (
        ("OPENING BALANCE", ledger["opening_balance"]),
        (
            "TOTAL DEBIT",
            sum(row["debit"] for row in ledger["transactions"]),
        ),
        (
            "TOTAL CREDIT",
            sum(row["credit"] for row in ledger["transactions"]),
        ),
        ("CLOSING BALANCE", ledger["closing_balance"]),
    )
    summary_ranges = (("A", "B"), ("C", "D"), ("E", "F"), ("G", "I"))
    for (label, value), (start_column, end_column) in zip(
        summary_items, summary_ranges
    ):
        start = openpyxl.utils.column_index_from_string(start_column)
        end = openpyxl.utils.column_index_from_string(end_column)
        sheet.merge_cells(start_row=7, start_column=start, end_row=7, end_column=end)
        sheet.merge_cells(start_row=8, start_column=start, end_row=8, end_column=end)
        label_cell = sheet.cell(7, start, label)
        value_cell = sheet.cell(8, start, float(value or 0))
        label_cell.font = Font(name="Aptos", size=9, bold=True, color="52677D")
        label_cell.alignment = Alignment(horizontal="center", vertical="center")
        value_cell.font = Font(name="Aptos", size=13, bold=True, color="17324D")
        value_cell.alignment = Alignment(horizontal="center", vertical="center")
        value_cell.number_format = '"Rs. "#,##0.00;[Red]-"Rs. "#,##0.00'
        for row in (7, 8):
            for column in range(start, end + 1):
                sheet.cell(row, column).fill = pale_fill
                sheet.cell(row, column).border = Border(
                    bottom=Side(style="thin", color="FFFFFF")
                )
    sheet.row_dimensions[7].height = 20
    sheet.row_dimensions[8].height = 28

    headers = [
        "Date",
        "Transaction",
        "System Invoice No.",
        "Reference No.",
        "Payment Method",
        "Notes",
        "Debit (Rs.)",
        "Credit (Rs.)",
        "Balance (Rs.)",
    ]
    header_row = 10
    sheet.append([])
    sheet.append(headers)
    for cell in sheet[header_row]:
        cell.fill = blue_fill
        cell.font = white_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    sheet.row_dimensions[header_row].height = 28

    for row in ledger["transactions"]:
        sheet.append(
            [
                date.fromisoformat(row["date"]),
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

    first_data_row = header_row + 1
    last_data_row = header_row + len(ledger["transactions"])
    for row_number in range(first_data_row, last_data_row + 1):
        sheet.cell(row_number, 1).number_format = "dd mmm yyyy"
        sheet.row_dimensions[row_number].height = 23
        for column in range(1, 10):
            cell = sheet.cell(row_number, column)
            cell.font = Font(name="Aptos", size=9, color="243B53")
            cell.border = border_bottom
            cell.alignment = Alignment(
                vertical="center",
                horizontal="right" if column >= 7 else "left",
                wrap_text=column in (2, 4, 5, 6),
            )
            if (row_number - first_data_row) % 2:
                cell.fill = stripe_fill

    total_row = last_data_row + 1
    sheet.cell(total_row, 2, "TOTALS")
    sheet.cell(
        total_row,
        7,
        sum(row["debit"] for row in ledger["transactions"]),
    )
    sheet.cell(
        total_row,
        8,
        sum(row["credit"] for row in ledger["transactions"]),
    )
    for cell in sheet[total_row]:
        cell.fill = pale_fill
        cell.font = Font(name="Aptos", size=10, bold=True, color="17324D")
        cell.border = Border(top=Side(style="thin", color="2563EB"))

    for row in sheet.iter_rows(min_row=first_data_row, max_row=total_row, min_col=7, max_col=9):
        for cell in row:
            cell.number_format = '#,##0.00;[Red]-#,##0.00'
            cell.alignment = Alignment(horizontal="right", vertical="center")
    for column, width in enumerate((14, 22, 23, 20, 19, 38, 17, 17, 18), start=1):
        sheet.column_dimensions[openpyxl.utils.get_column_letter(column)].width = width
    sheet.freeze_panes = "A11"
    sheet.auto_filter.ref = f"A{header_row}:I{max(header_row, last_data_row)}"
    sheet.print_title_rows = f"{header_row}:{header_row}"
    sheet.sheet_properties.pageSetUpPr.fitToPage = True
    sheet.page_setup.orientation = "landscape"
    sheet.page_setup.paperSize = sheet.PAPERSIZE_A4
    sheet.page_setup.fitToWidth = 1
    sheet.page_setup.fitToHeight = 0
    sheet.page_margins.left = 0.25
    sheet.page_margins.right = 0.25
    sheet.page_margins.top = 0.5
    sheet.page_margins.bottom = 0.5
    sheet.print_area = f"A1:I{total_row}"

    buffer = BytesIO()
    workbook.save(buffer)
    buffer.seek(0)
    filename = f"Buyer_Ledger_{buyer.id}.xlsx"
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{buyer_id}/export/pdf")
def export_buyer_ledger_pdf(
    buyer_id: int,
    client_id: int,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    buyer, ledger = _buyer_ledger_export_data(
        buyer_id,
        client_id,
        from_date,
        to_date,
        db,
        current_user["id"],
    )

    page_size = landscape(A4)
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=page_size,
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=15 * mm,
        bottomMargin=18 * mm,
        title=f"Buyer Ledger - {buyer.name}",
        author="DI Invoicing",
    )
    navy = colors.HexColor("#17324D")
    blue = colors.HexColor("#2563EB")
    pale = colors.HexColor("#EEF5FC")
    stripe = colors.HexColor("#F7FAFD")
    ink = colors.HexColor("#243B53")
    muted = colors.HexColor("#64748B")
    border = colors.HexColor("#DCE5EF")
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "LedgerTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        alignment=TA_LEFT,
        textColor=navy,
        spaceAfter=2,
    )
    eyebrow_style = ParagraphStyle(
        "LedgerEyebrow",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        alignment=TA_RIGHT,
        textColor=blue,
    )
    subtitle_style = ParagraphStyle(
        "LedgerSubtitle",
        parent=styles["Normal"],
        fontSize=8,
        leading=11,
        textColor=muted,
    )
    meta_label_style = ParagraphStyle(
        "LedgerMetaLabel",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=7,
        leading=9,
        textColor=muted,
    )
    meta_value_style = ParagraphStyle(
        "LedgerMetaValue",
        parent=styles["Normal"],
        fontSize=8,
        leading=10,
        textColor=ink,
        splitLongWords=True,
    )
    summary_label_style = ParagraphStyle(
        "LedgerSummaryLabel",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=7,
        leading=9,
        textColor=muted,
        alignment=TA_LEFT,
    )
    summary_value_style = ParagraphStyle(
        "LedgerSummaryValue",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=15,
        textColor=navy,
    )
    section_style = ParagraphStyle(
        "LedgerSection",
        parent=styles["Heading3"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=12,
        textColor=navy,
        spaceBefore=4,
        spaceAfter=6,
    )
    cell_style = ParagraphStyle(
        "LedgerCell",
        parent=styles["Normal"],
        fontSize=7,
        leading=9,
        textColor=ink,
        splitLongWords=True,
    )
    cell_right_style = ParagraphStyle(
        "LedgerCellRight",
        parent=cell_style,
        alignment=TA_RIGHT,
    )
    header_style = ParagraphStyle(
        "LedgerTableHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=7,
        leading=8,
        textColor=colors.white,
        alignment=TA_LEFT,
    )
    header_right_style = ParagraphStyle(
        "LedgerTableHeaderRight",
        parent=header_style,
        alignment=TA_RIGHT,
    )

    period = (
        f"{from_date.isoformat() if from_date else 'Beginning'} to "
        f"{to_date.isoformat() if to_date else 'Current'}"
    )
    generated_at = datetime.now().strftime("%d %b %Y, %H:%M")
    transactions = ledger["transactions"]
    total_debit = sum(row["debit"] for row in transactions)
    total_credit = sum(row["credit"] for row in transactions)
    story = [
        Table(
            [[
                Paragraph("BUYER LEDGER", title_style),
                Paragraph("ACCOUNT STATEMENT", eyebrow_style),
            ]],
            colWidths=[doc.width * 0.68, doc.width * 0.32],
            style=TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]),
        ),
        Paragraph("Buyer account activity and running balance", subtitle_style),
        Spacer(1, 5 * mm),
    ]

    meta_table = Table(
        [
            [
                Paragraph("BUYER", meta_label_style),
                Paragraph(escape(str(buyer.name or "-")), meta_value_style),
                Paragraph("NTN/CNIC", meta_label_style),
                Paragraph(escape(str(buyer.ntn_cnic or "-")), meta_value_style),
            ],
            [
                Paragraph("PERIOD", meta_label_style),
                Paragraph(escape(period), meta_value_style),
                Paragraph("GENERATED", meta_label_style),
                Paragraph(escape(generated_at), meta_value_style),
            ],
        ],
        colWidths=[20 * mm, 88 * mm, 24 * mm, doc.width - 132 * mm],
    )
    meta_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F7FAFD")),
        ("BOX", (0, 0), (-1, -1), 0.5, border),
        ("INNERGRID", (0, 0), (-1, -1), 0.35, border),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    story.extend([meta_table, Spacer(1, 5 * mm)])

    summary_values = (
        ("OPENING BALANCE", ledger["opening_balance"]),
        ("TOTAL DEBIT", total_debit),
        ("TOTAL CREDIT", total_credit),
        ("CLOSING BALANCE", ledger["closing_balance"]),
    )
    summary_table = Table(
        [
            [
                Paragraph(label, summary_label_style)
                for label, _ in summary_values
            ],
            [
                Paragraph(f"Rs. {float(value or 0):,.2f}", summary_value_style)
                for _, value in summary_values
            ],
        ],
        colWidths=[doc.width / 4] * 4,
    )
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), pale),
        ("BOX", (0, 0), (-1, -1), 0.5, border),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.white),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 9),
        ("RIGHTPADDING", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    story.extend([
        summary_table,
        Spacer(1, 6 * mm),
        Paragraph("TRANSACTION DETAILS", section_style),
    ])

    headers = (
        "Date",
        "Transaction",
        "System invoice no.",
        "Reference no.",
        "Payment method",
        "Notes",
        "Debit (Rs.)",
        "Credit (Rs.)",
        "Balance (Rs.)",
    )
    table_data = [[
        Paragraph(escape(label), header_right_style if index >= 6 else header_style)
        for index, label in enumerate(headers)
    ]]
    for row in transactions:
        description = row["invoice_type"]
        if row.get("payment_method"):
            description = f"{description} ({row['payment_method']})"
        display_values = (
            date.fromisoformat(row["date"]).strftime("%d %b %Y"),
            description,
            row["invoice_number"],
            row["reference_number"],
            row["payment_method"],
            row["notes"],
        )
        table_data.append([
            Paragraph(escape(str(value or "-")), cell_style)
            for value in display_values
        ] + [
            Paragraph(
                f"{float(row['debit']):,.2f}" if row["debit"] else "-",
                cell_right_style,
            ),
            Paragraph(
                f"{float(row['credit']):,.2f}" if row["credit"] else "-",
                cell_right_style,
            ),
            Paragraph(f"{float(row['balance']):,.2f}", cell_right_style),
        ])

    if not transactions:
        table_data.append([
            Paragraph("No transactions for the selected period.", cell_style),
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
        ])
    total_row = len(table_data)
    table_data.append([
        Paragraph("TOTALS", ParagraphStyle(
            "LedgerTotalsLabel",
            parent=cell_style,
            fontName="Helvetica-Bold",
            textColor=navy,
        )),
        "",
        "",
        "",
        "",
        "",
        Paragraph(f"{float(total_debit):,.2f}", cell_right_style),
        Paragraph(f"{float(total_credit):,.2f}", cell_right_style),
        "",
    ])
    col_widths = [17, 35, 33, 26, 24, 46, 29, 29, 29]
    col_widths = [width * mm for width in col_widths]
    transaction_table = LongTable(
        table_data,
        colWidths=col_widths,
        repeatRows=1,
        hAlign="LEFT",
    )
    transaction_table_style = [
        ("BACKGROUND", (0, 0), (-1, 0), navy),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, 0), 0, navy),
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, blue),
        ("LINEBELOW", (0, 1), (-1, -2), 0.35, border),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("BACKGROUND", (0, total_row), (-1, total_row), pale),
        ("LINEABOVE", (0, total_row), (-1, total_row), 0.8, blue),
        ("SPAN", (0, total_row), (5, total_row)),
        ("ALIGN", (6, 0), (-1, -1), "RIGHT"),
    ]
    for row_index in range(1, total_row):
        if row_index % 2 == 0:
            transaction_table_style.append(
                ("BACKGROUND", (0, row_index), (-1, row_index), stripe)
            )
    if not transactions:
        transaction_table_style.append(("SPAN", (0, 1), (-1, 1)))
    transaction_table.setStyle(TableStyle(transaction_table_style))
    story.append(transaction_table)

    def draw_page(canvas, document):
        canvas.saveState()
        page_width, page_height = page_size
        canvas.setFillColor(blue)
        canvas.rect(0, page_height - 4 * mm, page_width, 4 * mm, fill=1, stroke=0)
        canvas.setStrokeColor(border)
        canvas.line(
            document.leftMargin,
            12 * mm,
            page_width - document.rightMargin,
            12 * mm,
        )
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(muted)
        canvas.drawString(
            document.leftMargin,
            8 * mm,
            f"DI Invoicing  |  Generated {generated_at}",
        )
        canvas.drawRightString(
            page_width - document.rightMargin,
            8 * mm,
            f"Page {document.page}",
        )
        canvas.restoreState()

    doc.build(story, onFirstPage=draw_page, onLaterPages=draw_page)
    buffer.seek(0)
    filename = f"Buyer_Ledger_{buyer.id}.pdf"
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
