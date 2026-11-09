from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.dependencies.auth_dependency import get_current_user

router = APIRouter(prefix="/products", tags=["products"])


def get_owned_client(db: Session, client_id: int, user_id: int):
    client = db.query(models.Client).filter(
        models.Client.id == client_id,
        models.Client.user_id == user_id,
    ).first()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        )
    return client


def get_owned_product(
    db: Session,
    product_id: int,
    client_id: int,
    user_id: int,
):
    product = (
        db.query(models.Product)
        .join(models.Client)
        .filter(
            models.Product.id == product_id,
            models.Product.client_id == client_id,
            models.Client.user_id == user_id,
        )
        .first()
    )
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )
    return product


@router.get("/", response_model=List[schemas.ProductOut])
def list_products(
    client_id: int,
    search: Optional[str] = Query(None, max_length=150),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    get_owned_client(db, client_id, current_user["id"])
    query = db.query(models.Product).filter(
        models.Product.client_id == client_id
    )
    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.filter(models.Product.name.ilike(term))
    return query.order_by(func.lower(models.Product.name)).all()


@router.post(
    "/",
    response_model=schemas.ProductOut,
    status_code=status.HTTP_201_CREATED,
)
def create_product(
    payload: schemas.ProductCreate,
    client_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    get_owned_client(db, client_id, current_user["id"])
    name = payload.name.strip()
    if not name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Product name is required",
        )
    duplicate = db.query(models.Product.id).filter(
        models.Product.client_id == client_id,
        func.lower(models.Product.name) == name.lower(),
    ).first()
    if duplicate:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A product with this name already exists",
        )
    product = models.Product(
        client_id=client_id,
        name=name,
        hs_code=payload.hs_code.strip() if payload.hs_code else None,
        stock_quantity=payload.stock_quantity,
    )
    db.add(product)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A product with this name already exists",
        )
    db.refresh(product)
    return product


@router.put("/{product_id}", response_model=schemas.ProductOut)
def update_product(
    product_id: int,
    payload: schemas.ProductUpdate,
    client_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    product = get_owned_product(
        db, product_id, client_id, current_user["id"]
    )
    updates = payload.model_dump(exclude_unset=True)
    required_values = ("name", "stock_quantity")
    if any(field in updates and updates[field] is None for field in required_values):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Name and stock cannot be null",
        )
    if "name" in updates:
        updates["name"] = updates["name"].strip()
        if not updates["name"]:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Product name cannot be empty",
            )
        duplicate = db.query(models.Product.id).filter(
            models.Product.client_id == client_id,
            models.Product.id != product_id,
            func.lower(models.Product.name) == updates["name"].lower(),
        ).first()
        if duplicate:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A product with this name already exists",
            )
    if updates.get("hs_code") is not None:
        updates["hs_code"] = updates["hs_code"].strip() or None
    for field, value in updates.items():
        setattr(product, field, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A product with this name already exists",
        )
    db.refresh(product)
    return product


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    product_id: int,
    client_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    product = get_owned_product(
        db, product_id, client_id, current_user["id"]
    )
    has_invoice_items = db.query(models.InvoiceItem.id).filter(
        models.InvoiceItem.product_id == product_id
    ).first()
    if has_invoice_items:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This product is used by invoices and cannot be deleted",
        )
    db.delete(product)
    db.commit()
