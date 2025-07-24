from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm
from models import schemas, db_models
from db.session import get_db
from core import security
from models.schemas import TokenRefreshRequest

router = APIRouter()


@router.post("/register", response_model=schemas.UserOut)
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    if (
        db.query(db_models.User)
        .filter(db_models.User.username == user.username)
        .first()
    ):
        raise HTTPException(status_code=400, detail="Username already exists")
    if db.query(db_models.User).filter(db_models.User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_pw = security.hash_password(user.password)
    db_user = db_models.User(
        username=user.username, email=user.email, hashed_password=hashed_pw
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@router.post("/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    user = (
        db.query(db_models.User)
        .filter(db_models.User.username == form_data.username)
        .first()
    )
    if not user or not security.verify_password(
        form_data.password, user.hashed_password
    ):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = security.create_access_token(data={"sub": user.username})
    refresh_token = security.create_refresh_token(data={"sub": user.username})

    # store refresh token
    db_token = db_models.RefreshToken(token=refresh_token, user_id=user.id)
    db.add(db_token)
    db.commit()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.post("/refresh", response_model=schemas.Token)
def refresh_token(token_data: TokenRefreshRequest, db: Session = Depends(get_db)):
    payload = security.verify_token(token_data.refresh_token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    username = payload.get("sub")
    user = db.query(db_models.User).filter_by(username=username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # check token exists in DB
    token_in_db = (
        db.query(db_models.RefreshToken)
        .filter_by(token=token_data.refresh_token)
        .first()
    )
    if not token_in_db:
        raise HTTPException(status_code=403, detail="Token not recognized")

    # issue new access token
    new_access_token = security.create_access_token(data={"sub": user.username})
    return {"access_token": new_access_token, "token_type": "bearer"}


@router.post("/logout")
def logout(token_data: TokenRefreshRequest, db: Session = Depends(get_db)):
    deleted = (
        db.query(db_models.RefreshToken)
        .filter_by(token=token_data.refresh_token)
        .delete()
    )
    db.commit()
    if not deleted:
        raise HTTPException(status_code=404, detail="Token not found")
    return {"detail": "Logged out"}
