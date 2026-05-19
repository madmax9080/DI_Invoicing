import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from .. import schemas, crud
from ..database import get_db
from app.dependencies.auth_dependency import get_current_user

router = APIRouter(
    prefix="/clients",
    tags=["clients"],
    responses={404: {"description": "Not found"}},
)

logger = logging.getLogger(__name__)

@router.post("/", response_model=schemas.ClientOut, status_code=status.HTTP_201_CREATED)
def create_client(
    client: schemas.ClientCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    db_client = crud.get_client_by_name(db, name=client.name, user_id=current_user["id"])
    if db_client:
        raise HTTPException(status_code=400, detail="Client with this name already exists")
    return crud.create_client(db, client, user_id=current_user["id"])

@router.get("/", response_model=List[schemas.ClientOut])
def read_clients(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return crud.get_clients(db, user_id=current_user["id"], skip=skip, limit=limit)

@router.get("/{client_id}", response_model=schemas.ClientOut)
def read_client(
    client_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    db_client = crud.get_client(db, client_id=client_id, user_id=current_user["id"])
    if db_client is None:
        raise HTTPException(status_code=404, detail="Client not found")
    return db_client

@router.put("/{client_id}", response_model=schemas.ClientOut)
def update_client(
    client_id: int,
    client: schemas.ClientUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    db_client = crud.update_client(
        db,
        client_id=client_id,
        user_id=current_user["id"],
        client_update=client
    )
    if db_client is None:
        raise HTTPException(status_code=404, detail="Client not found")
    return db_client

@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_client(
    client_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    success = crud.delete_client(db, client_id=client_id, user_id=current_user["id"])
    if not success:
        raise HTTPException(status_code=404, detail="Client not found")
    return None