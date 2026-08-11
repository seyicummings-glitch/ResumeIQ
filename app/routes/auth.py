from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import User
from app.schemas import (
    UserCreate,
    UserLogin,
    UserResponse,
    UserUpdate,
    PasswordChange,
    Token,
    PasswordResetRequest,
    PasswordResetConfirm,
)
from app.security import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
    create_password_reset_token,
    verify_password_reset_token,
    require_admin,
    normalize_email,
)
from app.services.email_service import is_email_configured, send_password_reset_email

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse)
def register(user: UserCreate, db: Session = Depends(get_db)):
    email = normalize_email(user.email)
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = User(
        email=email,
        hashed_password=hash_password(user.password),
        full_name=user.full_name
    )
    db.add(new_user)
    try:
        db.commit()
    except IntegrityError:
        # Guards the race between the existing_user check above and this commit
        # (two concurrent registrations for the same email) — the DB's unique
        # constraint is the real guarantee, this just keeps the error friendly.
        db.rollback()
        raise HTTPException(status_code=400, detail="Email already registered")
    db.refresh(new_user)
    return new_user


@router.post("/login", response_model=Token)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == normalize_email(credentials.email)).first()
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    if user.status in ("deactivated", "deleted"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been deactivated. Contact support if you believe this is a mistake."
        )

    user.last_login_at = datetime.now(timezone.utc)
    db.commit()

    access_token = create_access_token(data={"sub": str(user.id), "email": user.email})
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/me", response_model=UserResponse)
def update_me(
    data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if data.email is not None and normalize_email(data.email) != current_user.email:
        new_email = normalize_email(data.email)
        existing = db.query(User).filter(User.email == new_email).first()
        if existing:
            raise HTTPException(status_code=400, detail="That email is already registered to another account.")
        current_user.email = new_email

    profile_fields = data.model_dump(exclude_unset=True, exclude={"email"})
    for field, value in profile_fields.items():
        setattr(current_user, field, value)

    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/change-password")
def change_password(
    data: PasswordChange,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not verify_password(data.current_password, current_user.hashed_password):
        raise HTTPException(status_code=401, detail="Current password is incorrect.")

    current_user.hashed_password = hash_password(data.new_password)
    db.commit()

    return {"message": "Password updated successfully."}


@router.post("/logout")
def logout(current_user: User = Depends(get_current_user)):
    return {"message": "Successfully logged out. Please discard your access token."}


@router.post("/password-reset/request")
def request_password_reset(data: PasswordResetRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == normalize_email(data.email)).first()
    if not user:
        return {"message": "If that email exists, a reset link has been sent to it."}

    reset_token = create_password_reset_token(user.email)

    if not is_email_configured():
        # Dev fallback: no SMTP configured, so hand the token back directly
        # instead of silently failing to deliver a reset link.
        return {
            "message": "Password reset token generated.",
            "reset_token": reset_token
        }

    try:
        send_password_reset_email(user.email, reset_token)
    except Exception:
        raise HTTPException(status_code=500, detail="Could not send the reset email. Please try again later.")

    return {"message": "If that email exists, a reset link has been sent to it."}


@router.post("/password-reset/confirm")
def confirm_password_reset(data: PasswordResetConfirm, db: Session = Depends(get_db)):
    email = verify_password_reset_token(data.token)
    if not email:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.hashed_password = hash_password(data.new_password)
    db.commit()

    return {"message": "Password has been reset successfully."}


@router.get("/admin-only")
def admin_only_route(current_user: User = Depends(require_admin)):
    return {"message": f"Welcome, admin {current_user.email}!"}
