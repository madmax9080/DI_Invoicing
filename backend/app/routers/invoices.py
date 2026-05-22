import io
import json
from fastapi import APIRouter, Body, Depends, HTTPException, status, Query
import asyncio
import pandas as pd
from sqlalchemy.orm import joinedload
from sqlalchemy.orm import Session
from typing import Dict, List, Optional
import logging
from app.services.excel_parser import parse_excel
from app.services.invoice_builder import build_invoice_payloads_from_excel
from app.dependencies.auth_dependency import get_current_user
from ..dependencies.fbr import get_fbr_client_secure
from ..database import get_db
from .. import crud, models
from ..schemas import InvoiceCreate, InvoiceOut
from ..fbr_client import FBRClient
from datetime import date, datetime
from fastapi import UploadFile, File
from app.services.fbr_service import extract_fbr_invoice_numbers, post_to_fbr
from app.services.cache import clear_cache
from app.database import SessionLocal
from app.config import TEST_MODE

router = APIRouter(prefix="/invoices", tags=["invoices"])
logger = logging.getLogger(__name__)   
SEM_LIMIT = 2

@router.post("/post", status_code=status.HTTP_201_CREATED)
async def post_invoice_to_fbr(
    invoice: InvoiceCreate,
    fbr_client: FBRClient = Depends(get_fbr_client_secure),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    client_id = fbr_client.client_id
    internal_invoice_no = invoice.internalInvoiceNo
    if not internal_invoice_no:
        raise HTTPException(
            status_code=400,
            detail="Internal invoice number is required"
        )
    raw_payload = invoice.model_dump(mode="json")
    payload = raw_payload.copy()
    payload.pop("internalInvoiceNo", None)  # ✅ internal only
    existing = (
        db.query(models.Invoice)
        .filter(
            models.Invoice.client_id == client_id,
            models.Invoice.internal_invoice_no == internal_invoice_no
        )
        .first()
    )
    if existing:
        if existing.status == "posted":
            return {
                "status": "already_posted",
                "invoiceId": existing.id,
                "fbrInvoiceNumber": existing.fbrInvoiceNo,
            }
        if existing.status == "posting":
            raise HTTPException(
                status_code=409,
                detail="Invoice is already being processed",
            )
        db_invoice = existing
        db_invoice.status = "posting"
        db.commit()
    else:
        db_invoice = crud.create_invoice(
            db=db,
            payload=payload,
            response_data=None,
            status="posting",
            client_id=client_id,
            internal_invoice_no=internal_invoice_no,
            user_id=current_user["id"],
        )
    try:
        fbr_response = await fbr_client.post_invoice(payload)
        validation = fbr_response.get("validationResponse", {})
        business_status = validation.get("status")
        if business_status == "Invalid":
            db_invoice.status = "invalid"
            db_invoice.response_data = fbr_response
            db_invoice.error_message = validation.get("error")
            db.commit()
            return {
                "status": "invalid",
                "fbr_response": fbr_response,
            }
        extracted = extract_fbr_invoice_numbers(fbr_response)
        db_invoice.status = "posted"
        db_invoice.response_data = fbr_response
        db_invoice.fbrInvoiceNo = extracted["invoiceNumber"]
        db_invoice.error_message = None
        db.commit()
        clear_cache(f"dashboard:{client_id}:")
        clear_cache(f"reports:{client_id}:")
        db.refresh(db_invoice)
        return {
            "status": "success",
            "fbr_response": fbr_response,
            "fbrInvoiceNumber": extracted["invoiceNumber"],
            "itemInvoiceNumbers": extracted["itemInvoiceNumbers"],
            "invoiceId": db_invoice.id,
        }
    except Exception as exc:
        db_invoice.status = "failed"
        db_invoice.error_message = str(exc)
        db.commit()
        raise HTTPException(
            status_code=502,
            detail=str(exc)
        )

@router.post("/validate", status_code=status.HTTP_200_OK)
async def validate_invoice_with_fbr(
    invoice: InvoiceCreate,
    fbr_client: FBRClient = Depends(get_fbr_client_secure),
    db: Session = Depends(get_db),
):
    payload = invoice.model_dump(mode="json")
    try:
        fbr_response = await fbr_client.validate_invoice(payload)
        crud.create_invoice(
            db=db,
            payload=payload,
            response_data=fbr_response,
            status="validated",
            client_id=fbr_client.client_id,
        )
        return {
            "status": "valid",
            "fbrResponse": fbr_response,
        }
    except Exception as exc:
        crud.create_invoice(
            db=db,
            payload=payload,
            response_data=None,
            status="validation_failed",
            error_message=str(exc),
            client_id=fbr_client.client_id,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Validation failed: {str(exc)}",
        )

@router.get("/", response_model=List[InvoiceOut])
def list_invoices(
    skip: int = 0,
    limit: int = 50,
    status: Optional[str] = None,
    client_id: Optional[int] = None,
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    month: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = db.query(models.Invoice).join(models.Client).filter(
        models.Client.user_id == current_user["id"]
    ).options(joinedload(models.Invoice.items))
    if client_id:
        query = query.filter(models.Invoice.client_id == client_id)
    if status:
        query = query.filter(models.Invoice.status == status)
    if month:
        year, month_part = map(int, month.split("-"))
        start_date = datetime(year, month_part, 1)
        end_date = datetime(year + (month_part // 12), (month_part % 12) + 1, 1)
        query = query.filter(
            models.Invoice.invoiceDate >= start_date,
            models.Invoice.invoiceDate < end_date,
        )
    if date_from:
        query = query.filter(models.Invoice.invoiceDate >= date_from)
    if date_to:
        query = query.filter(models.Invoice.invoiceDate <= date_to)
    return query.order_by(models.Invoice.invoiceDate.desc()).offset(skip).limit(limit).all()

@router.post("/import-excel")
async def import_excel(
    file: UploadFile = File(...),
):
    contents = await file.read()
    df = parse_excel(contents)
    invoices = build_invoice_payloads_from_excel(df)
    return {
        "invoices": invoices
    }

@router.post("/preview-excel")
async def preview_excel(
    file: UploadFile = File(...),
):
    try:
        contents = await file.read()
        df = pd.read_excel(
            io.BytesIO(contents),
            dtype={
                "sellerNTNCNIC": str,
                "buyerNTNCNIC": str,
                "hsCode": str,
                "invoiceRefNo": str,
                "excelInvoiceId": str,
                "internalInvoiceNo": str,
            }
        )
        invoices = build_invoice_payloads_from_excel(df)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Excel parsing failed: {str(e)}")
    return {
        "totalInvoices": len(invoices),
        "invoices": invoices
    }

@router.post("/validate-excel")
async def validate_excel(
    invoices: List[Dict] = Body(...),
    client_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    client = db.query(models.Client).filter(
        models.Client.id == client_id,
        models.Client.user_id == current_user["id"]
    ).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    if not client.token:
        raise HTTPException(status_code=400, detail="Missing FBR token for client")
    fbr_client = FBRClient(token=client.token)
    SEM_LIMIT = 5
    semaphore = asyncio.Semaphore(SEM_LIMIT)
    async def validate_invoice(inv):
        async with semaphore:
            excel_id = inv.get("excelInvoiceId")
            payload = {
                k: v for k, v in inv.items()
                if k not in {"excelInvoiceId", "internalInvoiceNo"}
            }
            # ✅ DEBUG LOG HERE
            # print("\n========== FBR VALIDATE PAYLOAD ==========")
            # print(json.dumps(payload, indent=2, ensure_ascii=False))
            # print("=========================================\n")
            for attempt in range(2):
                try:
                    response = await asyncio.wait_for(
                        post_to_fbr(
                            url=f"{fbr_client.base_url}{fbr_client.validate_url}",
                            headers=fbr_client.headers,
                            payload=payload
                        ),
                        timeout=15
                    )
                    validation = response.get("validationResponse", {})
                    return {
                        "excelInvoiceId": excel_id,
                        "internalInvoiceNo": inv.get("internalInvoiceNo"),
                        "status": "valid" if validation.get("status") == "Valid" else "invalid",
                        "response": response
                    }
                except Exception as e:
                    error_text = str(e)
                    try:
                        json_part = error_text.split(":", 1)[-1].strip()
                        parsed = json.loads(json_part.replace("'", '"'))
                        validation = parsed.get("validationResponse", {})
                        return {
                            "excelInvoiceId": excel_id,
                            "status": "invalid",
                            "response": {
                                "validationResponse": validation
                            }
                        }
                    except:
                        pass
                    if "SUSPENDED" in error_text or "Runtime Error" in error_text:
                        return {
                            "excelInvoiceId": excel_id,
                            "status": "pending",
                            "error": error_text
                        }
                    if attempt == 0:
                        await asyncio.sleep(1)
                        continue
                    return {
                        "excelInvoiceId": excel_id,
                        "status": "invalid",
                        "error": error_text
                    }
    results = await asyncio.gather(
        *[validate_invoice(inv) for inv in invoices]
    )
    return {"results": results}

@router.post("/submit-excel")
async def submit_excel(
    invoices: List[Dict] = Body(...),
    client_id: int = Query(...),
    current_user=Depends(get_current_user),
):
    init_db: Session = SessionLocal()
    try:
        client = (
            init_db.query(models.Client)
            .filter(
                models.Client.id == client_id,
                models.Client.user_id == current_user["id"],
            )
            .first()
        )
        if not client:
            raise HTTPException(
                status_code=404,
                detail="Client not found",
            )
        if not client.token and not TEST_MODE:
            raise HTTPException(
                status_code=400,
                detail="Missing FBR token for client",
            )
        token = client.token
    finally:
        init_db.close()
    semaphore = asyncio.Semaphore(SEM_LIMIT)
    async def submit_invoice(inv: Dict):
        async with semaphore:
            db: Session = SessionLocal()
            try:
                excel_id = inv.get(
                    "excelInvoiceId"
                )
                internal_invoice_no = inv.get(
                    "internalInvoiceNo"
                )
                if not internal_invoice_no:
                    return {
                        "excelInvoiceId": excel_id,
                        "status": "failed",
                        "message": (
                            "Missing internal invoice number"
                        ),
                    }
                payload = {
                    k: v
                    for k, v in inv.items()
                    if k not in [
                        "excelInvoiceId",
                        "internalInvoiceNo",
                    ]
                }
                existing = (
                    db.query(models.Invoice)
                    .filter(
                        models.Invoice.client_id
                        == client_id,
                        models.Invoice.internal_invoice_no
                        == internal_invoice_no,
                    )
                    .first()
                )
                if existing:
                    if existing.status == "posted":
                        return {
                            "excelInvoiceId": excel_id,
                            "status": "already_posted",
                            "irn": existing.fbrInvoiceNo,
                        }
                    if existing.status == "posting":
                        return {
                            "excelInvoiceId": excel_id,
                            "status": "processing",
                            "error": (
                                "Invoice already being processed"
                            ),
                        }
                    if existing.status == "failed":
                        existing.status = "posting"
                        existing.error_message = None
                        db.commit()
                        db.refresh(existing)
                        db_invoice = existing
                    else:
                        return {
                            "excelInvoiceId": excel_id,
                            "status": "error",
                            "error": (
                                f"Cannot process invoice "
                                f"with status "
                                f"{existing.status}"
                            ),
                        }
                else:
                    db_invoice = crud.create_invoice(
                        db=db,
                        payload=payload,
                        response_data=None,
                        status="posting",
                        error_message=None,
                        client_id=client_id,
                        internal_invoice_no=internal_invoice_no,
                        user_id=current_user["id"],
                    )
                    db.commit()
                    db.refresh(db_invoice)
                print("TEST_MODE =", TEST_MODE)
                if TEST_MODE:
                    await asyncio.sleep(1)
                    response = {
                        "validationResponse": {
                            "status": "Valid"
                        },
                        "invoiceNumber": (
                            f"TEST-{internal_invoice_no}"
                        ),
                    }
                else:
                    fbr_client = FBRClient(
                        token=token
                    )
                    response = await asyncio.wait_for(
                        post_to_fbr(
                            url=(
                                f"{fbr_client.base_url}"
                                f"{fbr_client.post_url}"
                            ),
                            headers=fbr_client.headers,
                            payload=payload,
                        ),
                        timeout=20,
                    )
                validation = response.get(
                    "validationResponse",
                    {},
                )
                business_status = validation.get(
                    "status"
                )
                if business_status == "Invalid":
                    db_invoice.status = "failed"
                    db_invoice.response_data = (
                        response
                    )
                    db_invoice.error_message = (
                        validation.get("error")
                    )
                    db.commit()
                    return {
                        "excelInvoiceId": excel_id,
                        "status": "invalid",
                        "error": validation.get(
                            "error"
                        ),
                        "response": response,
                    }
                if TEST_MODE:
                    extracted = {
                        "invoiceNumber": response.get(
                            "invoiceNumber"
                        )
                    }
                else:
                    extracted = (
                        extract_fbr_invoice_numbers(
                            response
                        )
                    )
                db_invoice.status = "posted"
                db_invoice.response_data = (
                    response
                )
                db_invoice.fbrInvoiceNo = (
                    extracted.get(
                        "invoiceNumber"
                    )
                )
                db_invoice.error_message = None
                db.commit()
                return {
                    "excelInvoiceId": excel_id,
                    "status": "success",
                    "irn": extracted.get(
                        "invoiceNumber"
                    ),
                    "response": response,
                }
            except Exception as e:
                db.rollback()
                try:
                    if "db_invoice" in locals():
                        db_invoice.status = "failed"
                        db_invoice.error_message = (
                            str(e)
                        )
                        db.commit()
                except Exception:
                    db.rollback()
                return {
                    "excelInvoiceId": inv.get(
                        "excelInvoiceId"
                    ),
                    "status": "failed",
                    "error": str(e),
                }
            finally:
                db.close()
    results = await asyncio.gather(
        *[
            submit_invoice(inv)
            for inv in invoices
        ]
    )
    return {
        "results": results
    }

# @router.post("/submit-excel")
# async def submit_excel(
#     invoices: List[Dict] = Body(...),
#     client_id: int = Query(...),
#     current_user=Depends(get_current_user),
# ):
#     """
#     Safe bulk invoice submission flow:
#     1. Separate DB session per coroutine
#     2. Create invoice locally BEFORE FBR post
#     3. Commit posting state immediately
#     4. Rollback on every exception
#     5. Prevent duplicate posting
#     """
#     init_db: Session = SessionLocal()
#     try:
#         client = (
#             init_db.query(models.Client)
#             .filter(
#                 models.Client.id == client_id,
#                 models.Client.user_id == current_user["id"],
#             )
#             .first()
#         )
#         if not client:
#             raise HTTPException(
#                 status_code=404,
#                 detail="Client not found",
#             )
#         if not client.token:
#             raise HTTPException(
#                 status_code=400,
#                 detail="Missing FBR token for client",
#             )
#         token = client.token
#     finally:
#         init_db.close()
#     semaphore = asyncio.Semaphore(SEM_LIMIT)
#     async def submit_invoice(inv: Dict):
#         async with semaphore:
#             db: Session = SessionLocal()
#             try:
#                 excel_id = inv.get("excelInvoiceId")
#                 internal_invoice_no = (
#                     inv.get("internalInvoiceNo")
#                 )
#                 if not internal_invoice_no:
#                     return {
#                         "excelInvoiceId": excel_id,
#                         "status": "failed",
#                         "message": "Missing internal invoice number",
#                     }
#                 payload = {
#                     k: v
#                     for k, v in inv.items()
#                     if k
#                     not in [
#                         "excelInvoiceId",
#                         "internalInvoiceNo",
#                     ]
#                 }
#                 existing = (
#                     db.query(models.Invoice)
#                     .filter(
#                         models.Invoice.client_id
#                         == client_id,
#                         models.Invoice.internal_invoice_no
#                         == internal_invoice_no,
#                     )
#                     .first()
#                 )
#                 if existing:
#                     if existing.status == "posted":
#                         return {
#                             "excelInvoiceId": excel_id,
#                             "status": "already_posted",
#                             "irn": existing.fbrInvoiceNo,
#                         }
#                     if existing.status == "posting":
#                         return {
#                             "excelInvoiceId": excel_id,
#                             "status": "processing",
#                             "error": "Invoice already being processed",
#                         }
#                     if existing.status == "failed":
#                         existing.status = "posting"
#                         existing.error_message = None
#                         db.commit()
#                         db.refresh(existing)
#                         db_invoice = existing
#                     else:
#                         return {
#                             "excelInvoiceId": excel_id,
#                             "status": "error",
#                             "error": (
#                                 f"Cannot process invoice "
#                                 f"with status {existing.status}"
#                             ),
#                         }
#                 else:
#                     db_invoice = crud.create_invoice(
#                         db=db,
#                         payload=payload,
#                         response_data=None,
#                         status="posting",
#                         error_message=None,
#                         client_id=client_id,
#                         internal_invoice_no=internal_invoice_no,
#                     )
#                     db.commit()
#                     db.refresh(db_invoice)
#                 fbr_client = FBRClient(token=token)
#                 response = await asyncio.wait_for(
#                     post_to_fbr(
#                         url=(
#                             f"{fbr_client.base_url}"
#                             f"{fbr_client.post_url}"
#                         ),
#                         headers=fbr_client.headers,
#                         payload=payload,
#                     ),
#                     timeout=20,
#                 )
#                 validation = response.get(
#                     "validationResponse",
#                     {},
#                 )
#                 business_status = validation.get(
#                     "status"
#                 )
#                 if business_status == "Invalid":
#                     db_invoice.status = "failed"
#                     db_invoice.response_data = response
#                     db_invoice.error_message = (
#                         validation.get("error")
#                     )
#                     db.commit()
#                     return {
#                         "excelInvoiceId": excel_id,
#                         "status": "invalid",
#                         "error": validation.get("error"),
#                         "response": response,
#                     }
#                 extracted = (
#                     extract_fbr_invoice_numbers(
#                         response
#                     )
#                 )
#                 db_invoice.status = "posted"
#                 db_invoice.response_data = response
#                 db_invoice.fbrInvoiceNo = (
#                     extracted.get("invoiceNumber")
#                 )
#                 db_invoice.error_message = None
#                 db.commit()
#                 return {
#                     "excelInvoiceId": excel_id,
#                     "status": "success",
#                     "irn": extracted.get(
#                         "invoiceNumber"
#                     ),
#                     "response": response,
#                 }
#             except Exception as e:
#                 db.rollback()
#                 try:
#                     if "db_invoice" in locals():
#                         db_invoice.status = "failed"
#                         db_invoice.error_message = str(e)
#                         db.commit()
#                 except Exception:
#                     db.rollback()
#                 return {
#                     "excelInvoiceId": inv.get(
#                         "excelInvoiceId"
#                     ),
#                     "status": "failed",
#                     "error": str(e),
#                 }
#             finally:
#                 db.close()
#     results = await asyncio.gather(
#         *[
#             submit_invoice(inv)
#             for inv in invoices
#         ]
#     )
#     return {
#         "results": results
#     }

@router.get("/{invoice_id}", response_model=InvoiceOut)
def get_invoice_detail(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    invoice = crud.get_invoice(db, invoice_id, current_user["id"])
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice

@router.delete("/{invoice_id}", status_code=status.HTTP_200_OK)
def delete_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    invoice = db.query(models.Invoice).join(models.Client).filter(
        models.Invoice.id == invoice_id,
        models.Client.user_id == current_user["id"]
    ).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if invoice.status == "posted":
        raise HTTPException(status_code=400, detail="Posted invoices cannot be deleted")
    allowed_status = ["failed", "invalid", "validation_failed", "pending"]
    if invoice.status not in allowed_status:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete invoice with status '{invoice.status}'"
        )
    db.delete(invoice)
    db.commit()
    return {
        "success": True,
        "message": "Invoice deleted successfully"
    }