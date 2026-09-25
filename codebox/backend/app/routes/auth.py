from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..models import User
from ..schemas import LoginRequest, RegisterRequest, TokenResponse, UserOut
from ..services.auth import authenticate, create_access_token, get_current_user, hash_password
from ..services.email_checks import check_email_address
from ..services.rate_limit import client_ip, enforce

router = APIRouter(prefix="/auth", tags=["auth"])


def _token(user: User) -> TokenResponse:
    return TokenResponse(access_token=create_access_token(user.id), user=UserOut.model_validate(user))


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    enforce(f"register:{client_ip(request)}", get_settings().rate_limit_login_per_minute)
    email = check_email_address(body.email)
    existing = db.scalar(select(User).where(or_(User.username == body.username, User.email == email)))
    if existing is not None:
        if existing.email == email:
            raise HTTPException(status.HTTP_409_CONFLICT,
                                "An account with this email already exists. Try signing in instead.")
        raise HTTPException(status.HTTP_409_CONFLICT, "That username is already taken. Please choose another.")
    user = User(username=body.username, email=email, password_hash=hash_password(body.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:  # concurrent registration with the same name
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "That username or email was just taken. Please try again.")
    return _token(user)


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, request: Request, db: Session = Depends(get_db)):
    limit = get_settings().rate_limit_login_per_minute
    enforce(f"login-ip:{client_ip(request)}", limit * 3)
    enforce(f"login-user:{body.username.strip().lower()}", limit)
    user = authenticate(db, body.username, body.password)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid username or password")
    return _token(user)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user
