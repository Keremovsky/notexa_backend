from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from utils.user_utils import get_current_user
from models import schemas, db_models
from db.session import get_db
from models.db_models import User
from core import security
from models.schemas import TokenRefreshRequest, UserOut

router = APIRouter()


@router.post("/register")
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

    return {"detail": "Registered"}


@router.post("/login")
def login(form_data: schemas.UserLogin, db: Session = Depends(get_db)):
    db_user = (
        db.query(db_models.User)
        .filter(db_models.User.username == form_data.username)
        .first()
    )
    if not db_user or not security.verify_password(
        form_data.password, db_user.hashed_password
    ):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = security.create_access_token(data={"sub": str(db_user.id)})
    refresh_token = security.create_refresh_token(data={"sub": str(db_user.id)})

    db.query(db_models.RefreshToken).filter(
        db_user.id == db_models.RefreshToken.user_id
    ).delete()

    # store refresh token
    db_token = db_models.RefreshToken(token=refresh_token, user_id=db_user.id)
    db.add(db_token)
    db.commit()

    return UserOut(
        username=db_user.username,
        email=db_user.email,
        access=access_token,
        refresh=refresh_token,
    )


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
    new_access_token = security.create_access_token(data={"sub": str(user.id)})
    return {"access": new_access_token}


@router.post("/auto_login")
async def auto_login(token: TokenRefreshRequest, db: Session = Depends(get_db)):
    db_user = (
        db.query(db_models.User)
        .join(db_models.RefreshToken)
        .filter(db_models.RefreshToken.token == token.refresh_token)
        .first()
    )

    if not db_user:
        raise HTTPException(status_code=404, detail="No refresh token found")

    access_token = security.create_access_token(data={"sub": str(db_user.id)})

    return UserOut(
        username=db_user.username,
        email=db_user.email,
        access=access_token,
        refresh=token.refresh_token,
    )


@router.post("/logout")
def logout(
    token_data: TokenRefreshRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db_token = (
        db.query(db_models.RefreshToken)
        .filter(db_models.RefreshToken.user_id == current_user.id)
        .first()
    )

    if not (db_token.token == token_data.refresh_token):
        raise HTTPException(status_code=401, detail="No permission for logout")

    deleted = (
        db.query(db_models.RefreshToken)
        .filter_by(token=token_data.refresh_token)
        .delete()
    )
    db.commit()

    if not deleted:
        raise HTTPException(status_code=404, detail="Token not found")
    return {"detail": "Logged out"}
