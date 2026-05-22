from typing import Optional
from datetime import timezone
from psycopg2 import IntegrityError
from sqlalchemy.orm import Session
from . import models, schemas
from datetime import datetime
from decimal import Decimal
from typing import Optional, Union
from sqlalchemy import or_

def update_reference_cache(db: Session, endpoint: str, data: dict):
    cache = db.query(models.ReferenceCache).filter(models.ReferenceCache.endpoint == endpoint).first()
    if cache:
        cache.data_json = data
        cache.last_updated = datetime.now(timezone.utc)
    else:
        cache = models.ReferenceCache(endpoint=endpoint, data_json=data)
        db.add(cache)
    db.commit()
    db.refresh(cache)
    return cache

def get_cached_reference(db: Session, endpoint: str,):
    return db.query(models.ReferenceCache).filter(models.ReferenceCache.endpoint == endpoint).first()

def normalize_for_db(value: Union[str, int, float, None]) -> Optional[Decimal]:
    if value == "" or value is None:
        return None
    return Decimal(str(value))

def create_invoice(
        db: Session, 
        payload: dict,
        response_data: dict = None, 
        status: str = "pending", 
        error_message: str = None, 
        client_id: Optional[int] = None, 
        user_id: Optional[int] = None,
        fbr_invoice_no: Optional[str] = None, 
        internal_invoice_no=None
    ):
    try:
        buyer = get_or_create_buyer(db, payload, client_id, user_id) 
        db_invoice = models.Invoice(
            invoiceRefNo=payload.get("invoiceRefNo"),
            internal_invoice_no=internal_invoice_no,
            fbrInvoiceNo=fbr_invoice_no,
            invoiceType=payload["invoiceType"],
            invoiceDate=datetime.fromisoformat(payload["invoiceDate"]),
            sellerNTNCNIC=payload["sellerNTNCNIC"],     
            sellerBusinessName=payload["sellerBusinessName"],
            sellerProvince=payload["sellerProvince"],
            sellerAddress=payload.get("sellerAddress"),     
            buyerNTNCNIC=payload.get("buyerNTNCNIC"),
            buyerBusinessName=payload.get("buyerBusinessName"),
            buyerProvince=payload.get("buyerProvince"),
            buyerAddress=payload.get("buyerAddress"),
            buyerRegistrationType=payload.get("buyerRegistrationType"),
            scenarioId=payload.get("scenarioId"),
            status=status,
            request_payload=payload,
            response_data=response_data,
            error_message=error_message,
            client_id=client_id,
            buyer_id=buyer.id if buyer else None,
        )
        db.add(db_invoice)
        db.flush()
        for item in payload["items"]:
            db_item = models.InvoiceItem(
                invoice_id=db_invoice.id,
                hsCode=item["hsCode"],
                productDescription=item["productDescription"],
                uom=item.get("uoM"), 
                quantity=item["quantity"],
                rate=item["rate"],
                valueSalesExcludingST=item["valueSalesExcludingST"],
                salesTaxApplicable=item["salesTaxApplicable"],
                furtherTax=item.get("furtherTax"),
                extraTax=normalize_for_db(item.get("extraTax")),
                fedPayable=item.get("fedPayable"),
                discount=item.get("discount"),
                totalValues=item.get("totalValues"),                   
                fixedNotifiedValueOrRetailPrice=item.get("fixedNotifiedValueOrRetailPrice"),
                salesTaxWithheldAtSource=item.get("salesTaxWithheldAtSource"),
                sroScheduleNo=item.get("sroScheduleNo", ""),           
                sroItemSerialNo=item.get("sroItemSerialNo", ""),
                saleType=item.get("saleType"), 
            )
            db.add(db_item)
        db.commit()    
        db.refresh(db_invoice)
        return db_invoice
    except Exception as e:
        db.rollback()
        raise e

def normalize_ntn(ntn: str):
    return ntn.replace("-", "").strip()

def get_or_create_buyer(
    db: Session,
    payload: dict,
    client_id: int,
    user_id: int,
):
    client = (
        db.query(models.Client)
        .filter(
            models.Client.id == client_id,
            models.Client.user_id == user_id,
        )
        .first()
    )
    if not client:
        raise ValueError("Invalid client access")
    ntn = normalize_ntn(
        payload.get("buyerNTNCNIC") or ""
    )
    if not ntn:
        return None
    buyer = (
        db.query(models.Buyer)
        .filter(
            models.Buyer.ntn_cnic == ntn,
            models.Buyer.client_id == client_id
        )
        .first()
    )
    if buyer:
        buyer.name = (
            payload.get("buyerBusinessName")
            or buyer.name
        )
        buyer.province = (
            payload.get("buyerProvince")
            or buyer.province
        )
        buyer.address = (
            payload.get("buyerAddress")
            or buyer.address
        )
        buyer.buyer_registration_type = (
            payload.get("buyerRegistrationType")
            or buyer.buyer_registration_type
        )
        db.flush()
        return buyer
    buyer = models.Buyer(
        ntn_cnic=ntn,
        name=payload.get("buyerBusinessName"),
        province=payload.get("buyerProvince"),
        address=payload.get("buyerAddress"),
        buyer_registration_type=payload.get(
            "buyerRegistrationType"
        ),
        client_id=client_id,
    )
    db.add(buyer)
    try:
        db.flush()
        return buyer
    except IntegrityError:
        db.expire_all()
        return (
            db.query(models.Buyer)
            .filter(
                models.Buyer.ntn_cnic == ntn,
                models.Buyer.client_id == client_id
            )
            .first()
        )
    
def create_buyer(
    db: Session,
    payload: schemas.BuyerCreate,
    client_id: int,
    user_id: int,
):
    client = (
        db.query(models.Client)
        .filter(
            models.Client.id == client_id,
            models.Client.user_id == user_id,
        )
        .first()
    )
    if not client:
        raise ValueError("Invalid client access")
    try:
        normalized_ntn = normalize_ntn(
            payload.ntn_cnic
        )
        buyer = models.Buyer(
            ntn_cnic=normalized_ntn,
            name=payload.name.strip(),
            province=payload.province,
            address=payload.address,
            buyer_registration_type=payload.buyer_registration_type,
            client_id=client_id,
        )
        db.add(buyer)
        db.commit()
        db.refresh(buyer)
        return buyer
    except IntegrityError:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise

def get_buyers(
    db: Session,
    client_id: int,
    user_id: int,
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
):
    query = (
        db.query(models.Buyer)
        .join(models.Client)
        .filter(
            models.Buyer.client_id == client_id,
            models.Client.user_id == user_id,
        )
    )
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                models.Buyer.name.ilike(search_term),
                models.Buyer.ntn_cnic.ilike(search_term),
            )
        )
    total = query.count()
    items = (
        query
        .order_by(models.Buyer.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return {
        "items": items,
        "total": total,
        "skip": skip,
        "limit": limit,
    }

def get_buyer_by_id(
    db: Session,
    buyer_id: int,
    client_id: int,
    user_id: int,
):
    return (
        db.query(models.Buyer)
        .join(models.Client)
        .filter(
            models.Buyer.id == buyer_id,
            models.Buyer.client_id == client_id,
            models.Client.user_id == user_id,
        )
        .first()
    )

def get_buyer_by_ntn(
    db: Session,
    ntn_cnic: str,
    client_id: int,
    user_id: int,
):
    normalized_ntn = normalize_ntn(ntn_cnic)
    return (
        db.query(models.Buyer)
        .join(models.Client)
        .filter(
            models.Buyer.ntn_cnic == normalized_ntn,
            models.Buyer.client_id == client_id,
            models.Client.user_id == user_id,
        )
        .first()
    )

def update_buyer(
    db: Session,
    buyer: models.Buyer,
    payload: schemas.BuyerUpdate,
):
    try:
        if payload.ntn_cnic is not None:
            buyer.ntn_cnic = normalize_ntn(payload.ntn_cnic)
        if payload.name is not None:
            buyer.name = payload.name.strip()
        if payload.province is not None:
            buyer.province = payload.province
        if payload.address is not None:
            buyer.address = payload.address
        if payload.buyer_registration_type is not None:
            buyer.buyer_registration_type = (
                payload.buyer_registration_type
            )
        db.commit()
        db.refresh(buyer)
        return buyer
    except IntegrityError:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise e

def delete_buyer(
    db: Session,
    buyer: models.Buyer,
):
    try:
        db.delete(buyer)
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        raise e   
    
def get_invoice(db: Session, invoice_id: int, user_id: int):
    return db.query(models.Invoice).join(models.Client).filter(
        models.Invoice.id == invoice_id,
        models.Client.user_id == user_id
    ).first()

def get_invoices(db: Session, user_id: int, skip: int = 0, limit: int = 100):
    return db.query(models.Invoice).join(models.Client).filter(
        models.Client.user_id == user_id
    ).offset(skip).limit(limit).all()

def create_client(db: Session, client: schemas.ClientCreate, user_id: int):
    db_client = models.Client(**client.model_dump(), user_id=user_id)
    db.add(db_client)
    db.commit()
    db.refresh(db_client)
    return db_client

def get_clients(db: Session, user_id: int, skip: int = 0, limit: int = 100):
    return db.query(models.Client)\
        .filter(models.Client.user_id == user_id)\
        .offset(skip)\
        .limit(limit)\
        .all()

def get_client(db: Session, client_id: int, user_id: int):
    return db.query(models.Client).filter(
        models.Client.id == client_id,
        models.Client.user_id == user_id
    ).first()

def get_client_by_name(db: Session, name: str, user_id: int):
    return db.query(models.Client).filter(
        models.Client.name == name,
        models.Client.user_id == user_id
    ).first()

def update_client(db: Session, client_id: int, user_id: int, client_update: schemas.ClientUpdate):
    db_client = get_client(db, client_id, user_id)
    if not db_client:
        return None
    update_data = client_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_client, key, value)
    db.commit()
    db.refresh(db_client)
    return db_client

def delete_client(db: Session, client_id: int, user_id: int):
    db_client = get_client(db, client_id, user_id)
    if not db_client:
        return False
    db.delete(db_client)
    db.commit()
    return True