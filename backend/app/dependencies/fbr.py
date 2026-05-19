from fastapi import HTTPException, Depends
from sqlalchemy.orm import Session
from app import models
from app.dependencies.auth_dependency import get_current_user
from ..database import get_db
from ..fbr_client import FBRClient

def get_fbr_client_secure(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> FBRClient:
    client = db.query(models.Client).filter(
        models.Client.id == client_id,
        models.Client.user_id == current_user["id"]
    ).first()
    if not client or not client.token:
        raise HTTPException(
            status_code=404,
            detail="Client not found or missing FBR token"
        )
    fbr = FBRClient(token=client.token)
    fbr.client_id = client.id
    return fbr