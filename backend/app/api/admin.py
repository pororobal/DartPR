"""Admin endpoints — manual plan management."""

import logging
from fastapi import APIRouter, Depends, HTTPException, Header
from typing import Optional

from app.services.supabase_client import get_supabase
from app.schemas.auth import PlanUpdateRequest, UserResponse
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(tags=["admin"])


# Simple admin key check (MVP — replace with proper auth later)
ADMIN_KEY = "dart0s-admin-2024"  # TODO: move to env var


async def verify_admin(x_admin_key: Optional[str] = Header(None)):
    """Simple header-based admin auth for MVP."""
    if not x_admin_key or x_admin_key != ADMIN_KEY:
        raise HTTPException(
            status_code=403,
            detail="Invalid admin key",
        )
    return True


@router.post("/users/{user_id}/plan", response_model=UserResponse)
async def update_user_plan(
    user_id: str,
    req: PlanUpdateRequest,
    _admin_ok: bool = Depends(verify_admin),
):
    """
    Manually update a user's plan.
    Called after admin confirms payment via KakaoTalk.
    """
    if req.plan not in ("free", "pro", "admin"):
        raise HTTPException(
            status_code=400,
            detail="Plan must be 'free', 'pro' or 'admin'",
        )

    supabase = get_supabase()

    # Check user exists
    existing = (
        supabase.table("users")
        .select("*")
        .eq("id", user_id)
        .maybe_single()
        .execute()
    )
    if not existing.data:
        raise HTTPException(status_code=404, detail="User not found")

    # Generate API key for developer plan
    update_data: dict = {
        "plan": req.plan,
        "plan_updated_by": req.updated_by,
        "plan_updated_at": "now()",
    }

    if req.plan_expires_at:
        update_data["plan_expires_at"] = req.plan_expires_at

    supabase.table("users").update(update_data).eq("id", user_id).execute()

    # Fetch updated user
    updated = (
        supabase.table("users")
        .select("*")
        .eq("id", user_id)
        .single()
        .execute()
    )

    row = updated.data
    return UserResponse(
        id=row["id"],
        email=row["email"],
        plan=row["plan"],
        api_key=row.get("api_key"),
        plan_expires_at=row.get("plan_expires_at"),
    )


@router.get("/users")
async def list_users(_admin_ok: bool = Depends(verify_admin)):
    """List all users (admin only)."""
    supabase = get_supabase()
    result = supabase.table("users").select("*").order("created_at", desc=True).execute()
    return {"data": result.data or []}
