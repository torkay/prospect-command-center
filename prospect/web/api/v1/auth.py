"""Authentication API endpoints."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from prospect.web.database import get_db, User
from prospect.web.auth import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    UserResponse,
    authenticate_user,
    create_user,
    create_access_token,
    get_current_user,
    get_user_by_email,
    get_password_hash,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse)
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """
    Register a new user account.

    Returns an access token on successful registration.
    """
    # Check if email already exists
    existing_user = get_user_by_email(db, request.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Validate password strength
    if len(request.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters",
        )

    # Create user
    user = create_user(
        db=db,
        email=request.email,
        password=request.password,
        name=request.name,
        company=request.company,
    )

    # Generate token
    access_token = create_access_token(user.id, user.email)

    return TokenResponse(
        access_token=access_token,
        user=UserResponse.model_validate(user),
    )


@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """
    Login with email and password.

    Returns an access token on successful authentication.
    """
    user = authenticate_user(db, request.email, request.password)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    # Update last login
    user.last_login_at = datetime.utcnow()
    db.commit()

    # Generate token
    access_token = create_access_token(user.id, user.email)

    return TokenResponse(
        access_token=access_token,
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """
    Get the current authenticated user's profile.
    """
    return UserResponse.model_validate(current_user)


class UpdateProfileRequest(BaseModel):
    """Update profile request."""
    name: Optional[str] = None
    company: Optional[str] = None


@router.patch("/me", response_model=UserResponse)
def update_me(
    request: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update the current user's profile.
    """
    if request.name is not None:
        current_user.name = request.name
    if request.company is not None:
        current_user.company = request.company

    db.commit()
    db.refresh(current_user)

    return UserResponse.model_validate(current_user)


class ChangePasswordRequest(BaseModel):
    """Change password request."""
    current_password: str
    new_password: str


@router.post("/change-password")
def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Change the current user's password.
    """
    # Verify current password
    from prospect.web.auth import verify_password
    if not verify_password(request.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    # Validate new password
    if len(request.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 8 characters",
        )

    # Update password
    current_user.password_hash = get_password_hash(request.new_password)
    db.commit()

    return {"message": "Password changed successfully"}


@router.post("/logout")
def logout(current_user: User = Depends(get_current_user)):
    """
    Logout the current user.

    Note: With JWT tokens, logout is handled client-side by discarding the token.
    This endpoint exists for API consistency and could be extended to implement
    token blacklisting if needed.
    """
    return {"message": "Logged out successfully"}


# Health check that doesn't require auth
@router.get("/health")
def health_check():
    """Check if auth service is healthy."""
    return {"status": "ok", "service": "auth"}
