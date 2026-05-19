from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from .. import schemas, crud
from ..database import get_db
from app.dependencies.auth_dependency import get_current_user
import logging

router = APIRouter(
    prefix="/buyers",
    tags=["buyers"],
    responses={404: {"description": "Not found"}},
)

logger = logging.getLogger(__name__)

def get_existing_buyer(
    buyer_id: int,
    client_id: int,
    user_id: int,
    db: Session,
):
    buyer = crud.get_buyer_by_id(
        db=db,
        buyer_id=buyer_id,
        client_id=client_id,
        user_id=user_id,
    )

    if not buyer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Buyer not found",
        )

    return buyer

@router.post(
    "/",
    response_model=schemas.BuyerResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_buyer(
    payload: schemas.BuyerCreate,
    client_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        return crud.create_buyer(
            db=db,
            payload=payload,
            client_id=client_id,
            user_id=current_user["id"],
        )

    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Buyer with this NTN/CNIC already exists"
            ),
        )


@router.get(
    "/",
    response_model=schemas.BuyerPaginationResponse
)
def get_buyers(
    client_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return crud.get_buyers(
        db=db,
        client_id=client_id,
        user_id=current_user["id"],
        skip=skip,
        limit=limit,
        search=search,
    )

@router.get(
    "/id/{buyer_id}",
    response_model=schemas.BuyerResponse,
)
def get_buyer_by_id(
    buyer_id: int,
    client_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return get_existing_buyer(
        buyer_id=buyer_id,
        client_id=client_id,
        user_id=current_user["id"],
        db=db,
    )

@router.get(
    "/ntn/{ntn_cnic}",
    response_model=schemas.BuyerResponse,
)
def get_buyer_by_ntn(
    ntn_cnic: str,
    client_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    buyer = crud.get_buyer_by_ntn(
        db=db,
        ntn_cnic=ntn_cnic,
        client_id=client_id,
        user_id=current_user["id"],
    )

    if not buyer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Buyer not found",
        )

    return buyer

@router.put(
    "/{buyer_id}",
    response_model=schemas.BuyerResponse,
)
def update_buyer(
    buyer_id: int,
    payload: schemas.BuyerUpdate,
    client_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    buyer = get_existing_buyer(
        buyer_id=buyer_id,
        client_id=client_id,
        user_id=current_user["id"],
        db=db,
    )
    try:
        return crud.update_buyer(
            db=db,
            buyer=buyer,
            payload=payload,
        )
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Buyer with this NTN/CNIC already exists"
            ),
        )

@router.delete(
    "/{buyer_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_buyer(
    buyer_id: int,
    client_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    buyer = get_existing_buyer(
        buyer_id=buyer_id,
        client_id=client_id,
        user_id=current_user["id"],
        db=db,
    )
    crud.delete_buyer(
        db=db,
        buyer=buyer,
    )
    return None