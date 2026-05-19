from fastapi import APIRouter, Depends, HTTPException, status
from app.database import get_db
from app.models import User
from app.schemas import ChangePasswordSchema, LoginSchema, RegisterSchema, Token
from sqlalchemy.orm import Session
from app.services.authenticate import hash_password, verify_password, create_access_token
from app.dependencies.auth_dependency import get_current_user

router = APIRouter(
    prefix="/auth",
    tags=["Auth"]
)

@router.post("/register")
def register(data: RegisterSchema, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already exists")
    password_hash = hash_password(data.password)
    new_user = User(
        email=data.email,
        password_hash=password_hash
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "User created"}

@router.post("/login", response_model=Token)
def login(data: LoginSchema, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid credentials")
    if not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Invalid credentials")
    token = create_access_token({
        "id": user.id,
        "email": user.email
    })
    return {"access_token": token, "token_type": "bearer"}

@router.post("/change-password")
def change_password(
    data: ChangePasswordSchema,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    user = db.query(User).filter(User.id == current_user["id"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not verify_password(data.old_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Old password is incorrect"
        )
    new_hashed_password = hash_password(data.new_password)
    user.password_hash = new_hashed_password
    db.commit()
    return {"message": "Password changed successfully"}