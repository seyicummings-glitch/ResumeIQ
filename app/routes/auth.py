import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import User, PendingRegistration
from app.schemas import (
    UserCreate,
    UserLogin,
    UserResponse,
    UserUpdate,
    PasswordChange,
    Token,
    PasswordResetRequest,
    PasswordResetConfirm,
    RegisterResponse,
    EmailVerificationConfirm,
    ResendVerificationRequest,
)
from app.security import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
    create_password_reset_token,
    verify_password_reset_token,
    create_email_verification_token,
    verify_email_verification_token,
    require_admin,
    normalize_email,
)
from app.services.analytics import track_event, EVENT_TYPES, FEATURE_AUTH
from app.services.email_service import is_email_configured, send_password_reset_email, send_verification_email
from app.services.feature_gate import grant_signup_credits

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=RegisterResponse)
def register(user: UserCreate, db: Session = Depends(get_db), request: Request = None):
    # UserCreate.email already rejected bad formats, disposable providers, and
    # domains with no mail servers at all (see app/schemas.py) before this runs.
    email = normalize_email(user.email)
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # No User row is created here — only a pending registration. The real
    # account (see verify_email() below) doesn't exist until the emailed link
    # is clicked, so a fake or unreachable address never results in an account
    # at all, not even a locked one. Re-registering the same still-unverified
    # address (e.g. retrying after a typo'd password) just overwrites the
    # pending row and issues a fresh token.
    pending = db.query(PendingRegistration).filter(PendingRegistration.email == email).first()
    if pending:
        pending.hashed_password = hash_password(user.password)
        pending.full_name = user.full_name
    else:
        pending = PendingRegistration(
            email=email,
            hashed_password=hash_password(user.password),
            full_name=user.full_name,
        )
        db.add(pending)
    db.commit()

    verification_token = create_email_verification_token(email)

    if not is_email_configured():
        # Dev fallback: no SMTP configured, so hand the token back directly
        # instead of silently failing to deliver a verification link.
        return {
            "message": "This app isn't sending real emails yet — use the token below to verify and finish creating your account.",
            "email": email,
            "verification_token": verification_token,
        }

    try:
        send_verification_email(email, verification_token)
    except Exception:
        # Nothing durable exists yet besides the pending row — surface the
        # failure so the user knows to retry, rather than claiming success for
        # a link that never arrived.
        raise HTTPException(status_code=500, detail="Could not send the verification email. Please try again later.")

    return {
        "message": "Check your email to verify your address and finish creating your account.",
        "email": email,
        "verification_token": None,
    }


@router.post("/login", response_model=Token)
def login(credentials: UserLogin, db: Session = Depends(get_db), request: Request = None):
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

    if not user.is_verified:
        # Structured detail (not a plain string) so the frontend can tell this apart
        # from other 403s and offer a "resend verification email" action instead of
        # just displaying the message — see client.js's extractErrorMessage().
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "email_not_verified",
                "message": "Please verify your email before logging in. Check your inbox for the link, or request a new one.",
            },
        )

    user.last_login_at = datetime.now(timezone.utc)
    db.commit()

    # A fresh session_id per login, embedded in the token itself (stateless — no
    # session table) so every request during this login "session" can be
    # correlated in analytics without the client doing anything extra.
    session_id = str(uuid.uuid4())
    access_token = create_access_token(data={"sub": str(user.id), "email": user.email, "session_id": session_id})

    track_event(db, EVENT_TYPES["USER_LOGIN"], FEATURE_AUTH, user_id=user.id, request=request, session_id=session_id)
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/me", response_model=UserResponse)
def update_me(
    data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    request: Request = None,
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

    track_event(
        db, EVENT_TYPES["PROFILE_UPDATED"], FEATURE_AUTH, user_id=current_user.id,
        metadata={"fields": sorted(profile_fields.keys())}, request=request,
    )
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
def logout(current_user: User = Depends(get_current_user), db: Session = Depends(get_db), request: Request = None):
    track_event(db, EVENT_TYPES["USER_LOGOUT"], FEATURE_AUTH, user_id=current_user.id, request=request)
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
def confirm_password_reset(data: PasswordResetConfirm, db: Session = Depends(get_db), request: Request = None):
    email = verify_password_reset_token(data.token)
    if not email:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.hashed_password = hash_password(data.new_password)
    db.commit()

    track_event(db, EVENT_TYPES["PASSWORD_RESET"], FEATURE_AUTH, user_id=user.id, request=request)
    return {"message": "Password has been reset successfully."}


@router.post("/verify-email")
def verify_email(data: EmailVerificationConfirm, db: Session = Depends(get_db), request: Request = None):
    email = verify_email_verification_token(data.token)
    if not email:
        raise HTTPException(status_code=400, detail="Invalid or expired verification link.")

    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        # Already verified — link clicked twice, or in a second tab. Idempotent
        # success rather than an error, since the end state is the same.
        return {"message": "Email verified — you can now log in."}

    pending = db.query(PendingRegistration).filter(PendingRegistration.email == email).first()
    if not pending:
        raise HTTPException(status_code=400, detail="Invalid or expired verification link.")

    # This is where the account actually comes into existence — see register()'s
    # docstring comment for why nothing durable existed before this.
    new_user = User(
        email=pending.email,
        hashed_password=pending.hashed_password,
        full_name=pending.full_name,
        is_verified=True,
    )
    db.add(new_user)
    db.delete(pending)
    try:
        db.commit()
    except IntegrityError:
        # Race: two verify-email requests for the same pending signup landed at
        # once. The DB's unique constraint is the real guarantee here.
        db.rollback()
        return {"message": "Email verified — you can now log in."}
    db.refresh(new_user)

    # Every new account starts with the admin-configured free token balance — see
    # app/services/feature_gate.py's docstring for the full token-economy model.
    grant_signup_credits(db, new_user)

    track_event(db, EVENT_TYPES["USER_REGISTERED"], FEATURE_AUTH, user_id=new_user.id, request=request)

    return {"message": "Email verified — you can now log in."}


@router.post("/resend-verification")
def resend_verification(data: ResendVerificationRequest, db: Session = Depends(get_db)):
    email = normalize_email(data.email)
    existing_user = db.query(User).filter(User.email == email).first()
    pending = db.query(PendingRegistration).filter(PendingRegistration.email == email).first()

    if existing_user or not pending:
        # Same non-enumerating shape whether the address is already verified or
        # there's no pending signup for it at all — don't let this endpoint
        # confirm which.
        return {"message": "If that email exists and needs verification, a new link has been sent."}

    verification_token = create_email_verification_token(email)

    if not is_email_configured():
        return {
            "message": "Verification token generated.",
            "verification_token": verification_token,
        }

    try:
        send_verification_email(email, verification_token)
    except Exception:
        raise HTTPException(status_code=500, detail="Could not send the verification email. Please try again later.")

    return {"message": "If that email exists and needs verification, a new link has been sent."}


@router.get("/admin-only")
def admin_only_route(current_user: User = Depends(require_admin)):
    return {"message": f"Welcome, admin {current_user.email}!"}
