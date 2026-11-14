from decimal import Decimal, ROUND_CEILING

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.dependencies.auth_dependency import get_current_user


router = APIRouter(prefix="/inventory", tags=["inventory"])


def _owned_client(db: Session, client_id: int, user_id: int) -> models.Client:
    client = db.query(models.Client).filter(
        models.Client.id == client_id,
        models.Client.user_id == user_id,
    ).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


def _get_products(
    db: Session,
    client_id: int,
    product_ids: set[int],
    *,
    lock: bool = False,
) -> dict[int, models.Product]:
    query = db.query(models.Product).filter(
        models.Product.client_id == client_id,
        models.Product.id.in_(product_ids),
    ).order_by(models.Product.id)
    if lock:
        query = query.with_for_update()
    products = query.all()
    by_id = {product.id: product for product in products}
    if by_id.keys() != product_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or more products were not found for this business",
        )
    return by_id


def _serialize_bom(db: Session, bom: models.ProductBOM) -> dict:
    product_ids = {
        bom.finished_product_id,
        *(component.component_product_id for component in bom.components),
    }
    products = _get_products(db, bom.client_id, product_ids)
    return {
        "id": bom.id,
        "finished_product_id": bom.finished_product_id,
        "finished_product_name": products[bom.finished_product_id].name,
        "finished_product_uom": products[bom.finished_product_id].uom,
        "components": [
            {
                "component_product_id": component.component_product_id,
                "component_product_name": products[component.component_product_id].name,
                "component_uom": products[component.component_product_id].uom,
                "quantity_per_unit": component.quantity_per_unit,
            }
            for component in bom.components
        ],
    }


@router.get("/movements")
def list_movements(
    client_id: int,
    limit: int = Query(default=100, ge=1, le=250),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _owned_client(db, client_id, current_user["id"])
    rows = (
        db.query(models.InventoryMovement, models.Product.name, models.Product.uom)
        .join(models.Product, models.Product.id == models.InventoryMovement.product_id)
        .filter(models.InventoryMovement.client_id == client_id)
        .order_by(
            models.InventoryMovement.movement_date.desc(),
            models.InventoryMovement.id.desc(),
        )
        .limit(limit)
        .all()
    )
    return [
        {
            "id": movement.id,
            "product_id": movement.product_id,
            "product_name": name,
            "uom": uom,
            "movement_type": movement.movement_type,
            "quantity": movement.quantity,
            "movement_date": movement.movement_date,
            "reference_type": movement.reference_type,
            "reference_id": movement.reference_id,
            "notes": movement.notes,
        }
        for movement, name, uom in rows
    ]


@router.get("/purchases")
def list_purchases(
    client_id: int,
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _owned_client(db, client_id, current_user["id"])
    receipts = (
        db.query(models.PurchaseReceipt)
        .filter(models.PurchaseReceipt.client_id == client_id)
        .order_by(
            models.PurchaseReceipt.received_date.desc(),
            models.PurchaseReceipt.id.desc(),
        )
        .limit(limit)
        .all()
    )
    product_ids = {
        item.product_id
        for receipt in receipts
        for item in receipt.items
    }
    products = _get_products(db, client_id, product_ids) if product_ids else {}
    return [
        {
            "id": receipt.id,
            "supplier_name": receipt.supplier_name,
            "supplier_reference": receipt.supplier_reference,
            "received_date": receipt.received_date,
            "notes": receipt.notes,
            "items": [
                {
                    "product_id": item.product_id,
                    "product_name": products[item.product_id].name,
                    "uom": products[item.product_id].uom,
                    "quantity": item.quantity,
                    "unit_cost": item.unit_cost,
                }
                for item in receipt.items
            ],
        }
        for receipt in receipts
    ]


@router.post(
    "/purchases",
    status_code=status.HTTP_201_CREATED,
)
def create_purchase(
    payload: schemas.PurchaseReceiptCreate,
    client_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _owned_client(db, client_id, current_user["id"])
    supplier_name = payload.supplier_name.strip()
    if not supplier_name:
        raise HTTPException(status_code=422, detail="Supplier name is required")
    product_ids = {item.product_id for item in payload.items}
    products = _get_products(db, client_id, product_ids, lock=True)
    receipt = models.PurchaseReceipt(
        client_id=client_id,
        supplier_name=supplier_name,
        supplier_reference=payload.supplier_reference.strip() if payload.supplier_reference else None,
        received_date=payload.received_date,
        notes=payload.notes.strip() if payload.notes else None,
        created_by=current_user["id"],
    )
    db.add(receipt)
    db.flush()
    for item in payload.items:
        product = products[item.product_id]
        product.stock_quantity += item.quantity
        receipt_item = models.PurchaseReceiptItem(
            receipt_id=receipt.id,
            product_id=product.id,
            quantity=item.quantity,
            unit_cost=item.unit_cost,
        )
        db.add(receipt_item)
        db.add(
            models.InventoryMovement(
                client_id=client_id,
                product_id=product.id,
                movement_type="purchase_receipt",
                quantity=item.quantity,
                movement_date=payload.received_date,
                reference_type="purchase",
                reference_id=receipt.id,
                notes=receipt.supplier_name,
                created_by=current_user["id"],
            )
        )
    db.commit()
    return {"id": receipt.id, "message": "Purchase receipt recorded"}


@router.get("/boms")
def list_boms(
    client_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _owned_client(db, client_id, current_user["id"])
    boms = (
        db.query(models.ProductBOM)
        .filter(models.ProductBOM.client_id == client_id)
        .order_by(models.ProductBOM.id)
        .all()
    )
    return [_serialize_bom(db, bom) for bom in boms]


@router.post("/boms", status_code=status.HTTP_201_CREATED)
def save_bom(
    payload: schemas.BOMCreate,
    client_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _owned_client(db, client_id, current_user["id"])
    product_ids = {
        payload.finished_product_id,
        *(component.component_product_id for component in payload.components),
    }
    products = _get_products(db, client_id, product_ids)
    finished_product = products[payload.finished_product_id]
    if finished_product.product_type != "finished_good":
        raise HTTPException(status_code=422, detail="BOM output must be a finished good")
    for component in payload.components:
        if products[component.component_product_id].product_type != "raw_material":
            raise HTTPException(
                status_code=422,
                detail="BOM components must be raw materials",
            )

    bom = db.query(models.ProductBOM).filter(
        models.ProductBOM.client_id == client_id,
        models.ProductBOM.finished_product_id == payload.finished_product_id,
    ).first()
    if not bom:
        bom = models.ProductBOM(
            client_id=client_id,
            finished_product_id=payload.finished_product_id,
        )
        db.add(bom)
        db.flush()
    else:
        db.query(models.ProductBOMComponent).filter(
            models.ProductBOMComponent.bom_id == bom.id
        ).delete(synchronize_session=False)
    for component in payload.components:
        db.add(
            models.ProductBOMComponent(
                bom_id=bom.id,
                component_product_id=component.component_product_id,
                quantity_per_unit=component.quantity_per_unit,
            )
        )
    db.commit()
    db.refresh(bom)
    return _serialize_bom(db, bom)


@router.get("/production-orders")
def list_production_orders(
    client_id: int,
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _owned_client(db, client_id, current_user["id"])
    orders = (
        db.query(models.ProductionOrder)
        .filter(models.ProductionOrder.client_id == client_id)
        .order_by(
            models.ProductionOrder.produced_date.desc(),
            models.ProductionOrder.id.desc(),
        )
        .limit(limit)
        .all()
    )
    product_ids = {
        product_id
        for order in orders
        for product_id in (
            [order.finished_product_id]
            + [component.component_product_id for component in order.components]
        )
    }
    products = _get_products(db, client_id, product_ids) if product_ids else {}
    return [
        {
            "id": order.id,
            "finished_product_id": order.finished_product_id,
            "finished_product_name": products[order.finished_product_id].name,
            "finished_product_uom": products[order.finished_product_id].uom,
            "quantity_produced": order.quantity_produced,
            "produced_date": order.produced_date,
            "notes": order.notes,
            "components": [
                {
                    "product_name": products[component.component_product_id].name,
                    "uom": products[component.component_product_id].uom,
                    "quantity_consumed": component.quantity_consumed,
                }
                for component in order.components
            ],
        }
        for order in orders
    ]


@router.post(
    "/production-orders",
    status_code=status.HTTP_201_CREATED,
)
def create_production_order(
    payload: schemas.ProductionOrderCreate,
    client_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _owned_client(db, client_id, current_user["id"])
    bom = db.query(models.ProductBOM).filter(
        models.ProductBOM.client_id == client_id,
        models.ProductBOM.finished_product_id == payload.finished_product_id,
    ).first()
    if not bom or not bom.components:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Save a BOM for this finished good before recording production",
        )

    required_ids = {
        payload.finished_product_id,
        *(component.component_product_id for component in bom.components),
    }
    products = _get_products(db, client_id, required_ids, lock=True)
    finished_product = products[payload.finished_product_id]
    if finished_product.product_type != "finished_good":
        raise HTTPException(status_code=422, detail="Production output must be a finished good")

    required_quantities = {
        component.component_product_id: (
            component.quantity_per_unit * payload.quantity_produced
        ).quantize(Decimal("0.0001"), rounding=ROUND_CEILING)
        for component in bom.components
    }
    for product_id, required_quantity in required_quantities.items():
        product = products[product_id]
        if product.product_type != "raw_material":
            raise HTTPException(
                status_code=409,
                detail=f"{product.name} is no longer classified as a raw material",
            )
        if product.stock_quantity < required_quantity:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Insufficient stock for {product.name}: "
                    f"{product.stock_quantity} {product.uom} available, "
                    f"{required_quantity} {product.uom} required"
                ),
            )

    order = models.ProductionOrder(
        client_id=client_id,
        finished_product_id=finished_product.id,
        quantity_produced=payload.quantity_produced,
        produced_date=payload.produced_date,
        notes=payload.notes.strip() if payload.notes else None,
        created_by=current_user["id"],
    )
    db.add(order)
    db.flush()
    for product_id, quantity in required_quantities.items():
        component_product = products[product_id]
        component_product.stock_quantity -= quantity
        db.add(
            models.ProductionOrderComponent(
                production_order_id=order.id,
                component_product_id=product_id,
                quantity_consumed=quantity,
            )
        )
        db.add(
            models.InventoryMovement(
                client_id=client_id,
                product_id=product_id,
                movement_type="production_consumption",
                quantity=-quantity,
                movement_date=payload.produced_date,
                reference_type="production",
                reference_id=order.id,
                notes=f"Used to produce {payload.quantity_produced} {finished_product.uom} {finished_product.name}",
                created_by=current_user["id"],
            )
        )
    finished_product.stock_quantity += payload.quantity_produced
    db.add(
        models.InventoryMovement(
            client_id=client_id,
            product_id=finished_product.id,
            movement_type="production_output",
            quantity=payload.quantity_produced,
            movement_date=payload.produced_date,
            reference_type="production",
            reference_id=order.id,
            notes=order.notes,
            created_by=current_user["id"],
        )
    )
    db.commit()
    return {"id": order.id, "message": "Production recorded"}

