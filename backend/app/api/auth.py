"""Auth endpoints — signup, login, logout, me."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.services.supabase_client import get_supabase, get_public_client
from app.schemas.auth import (
    SignupRequest,
    LoginRequest,
    AuthResponse,
    UserResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["auth"])
security = HTTPBearer(auto_error=False)


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict:
    """
    Extract and verify bearer token via Supabase Auth.
    Returns user dict with id, email, plan.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    token = credentials.credentials
    supabase = get_public_client()

    try:
        user_resp = supabase.auth.get_user(token)
        auth_user = user_resp.user
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {e}",
        )

    if not auth_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    # Look up plan from users table
    svc = get_supabase()
    user_row = (
        svc.table("users")
        .select("*")
        .eq("email", auth_user.email)
        .maybe_single()
        .execute()
    )

    return {
        "id": auth_user.id,
        "email": auth_user.email,
        "plan": user_row.data.get("plan", "free") if user_row.data else "free",
        "api_key": user_row.data.get("api_key") if user_row.data else None,
    }


def require_plan(min_plan: str = "pro"):
    """
    Dependency factory: require user to have at least a certain plan.
    Usage: `Depends(require_plan("pro"))`
    """
    async def _check(user: dict = Depends(get_current_user)) -> dict:
        plan_rank = {"free": 0, "pro": 1, "developer": 2}
        if plan_rank.get(user["plan"], -1) < plan_rank.get(min_plan, 0):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Plan '{min_plan}' or higher required. Current plan: {user['plan']}",
            )
        return user
    return _check


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/signup", response_model=AuthResponse)
async def signup(req: SignupRequest):
    """Register a new user with email + password."""
    supabase = get_public_client()

    try:
        auth_resp = supabase.auth.sign_up({
            "email": req.email,
            "password": req.password,
        })
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Signup failed: {e}",
        )

    user = auth_resp.user
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Signup failed — no user returned",
        )

    # Create row in users table
    svc = get_supabase()
    svc.table("users").insert({
        "id": user.id,
        "email": user.email,
        "plan": "free",
    }).execute()

    return AuthResponse(
        user=UserResponse(
            id=user.id,
            email=user.email or "",
            plan="free",
        ),
        access_token=auth_resp.session.access_token if auth_resp.session else "",
        refresh_token=auth_resp.session.refresh_token if auth_resp.session else None,
    )


@router.post("/login", response_model=AuthResponse)
async def login(req: LoginRequest):
    """Log in with email + password."""
    supabase = get_public_client()

    try:
        auth_resp = supabase.auth.sign_in_with_password({
            "email": req.email,
            "password": req.password,
        })
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Login failed: {e}",
        )

    user = auth_resp.user
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Login failed",
        )

    # Get plan
    svc = get_supabase()
    user_row = (
        svc.table("users")
        .select("*")
        .eq("email", user.email)
        .maybe_single()
        .execute()
    )
    plan = user_row.data.get("plan", "free") if user_row.data else "free"
    api_key = user_row.data.get("api_key") if user_row.data else None

    return AuthResponse(
        user=UserResponse(
            id=user.id,
            email=user.email or "",
            plan=plan,
            api_key=api_key,
        ),
        access_token=auth_resp.session.access_token,
        refresh_token=auth_resp.session.refresh_token,
    )


@router.post("/logout")
async def logout(user: dict = Depends(get_current_user)):
    """Log out the current user."""
    supabase = get_public_client()
    try:
        supabase.auth.sign_out()
    except Exception as e:
        logger.warning(f"Logout error (non-fatal): {e}")
    return {"message": "Logged out"}


@router.get("/me", response_model=UserResponse)
async def me(user: dict = Depends(get_current_user)):
    """Get current user info."""
    return UserResponse(
        id=user["id"],
        email=user["email"],
        plan=user["plan"],
        api_key=user.get("api_key"),
    )
