"""Notice board endpoints — admin write, public read."""

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.services.supabase_client import get_supabase
from app.api.auth import get_current_user, require_plan

logger = logging.getLogger(__name__)
router = APIRouter(tags=["notices"])


# ─── Schemas ───────────────────────────────────────────────────

class NoticeResponse(BaseModel):
    id: str
    title: str
    content: str
    author_email: str
    pinned: bool
    created_at: datetime
    updated_at: Optional[datetime] = None


class NoticeListResponse(BaseModel):
    data: list[NoticeResponse]
    total: int


class NoticeCreateRequest(BaseModel):
    title: str
    content: str
    pinned: bool = False


class NoticeUpdateRequest(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    pinned: Optional[bool] = None


# ─── Helpers ───────────────────────────────────────────────────

def _row_to_notice(row: dict) -> dict:
    return {
        "id": row["id"],
        "title": row["title"],
        "content": row["content"],
        "author_email": row.get("author_email", ""),
        "pinned": row.get("pinned", False),
        "created_at": row.get("created_at", ""),
        "updated_at": row.get("updated_at"),
    }


# ─── Endpoints ─────────────────────────────────────────────────

@router.get("/notices", response_model=NoticeListResponse)
async def list_notices(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=50),
):
    """Public: list notices (pinned first, then newest)."""
    supabase = get_supabase()

    # Pinned first, then by created_at desc
    result = (
        supabase.table("notices")
        .select("*", count="exact")
        .order("pinned", desc=True)
        .order("created_at", desc=True)
        .range((page - 1) * per_page, page * per_page - 1)
        .execute()
    )

    data = [_row_to_notice(r) for r in (result.data or [])]
    total = result.count if hasattr(result, "count") else len(data)

    return NoticeListResponse(data=data, total=total)


@router.get("/notices/{notice_id}", response_model=NoticeResponse)
async def get_notice(notice_id: str):
    """Public: get a single notice by ID."""
    supabase = get_supabase()
    result = (
        supabase.table("notices")
        .select("*")
        .eq("id", notice_id)
        .maybe_single()
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Notice not found")
    return _row_to_notice(result.data)


@router.post("/notices", response_model=NoticeResponse)
async def create_notice(
    req: NoticeCreateRequest,
    user: dict = Depends(require_plan("admin")),
):
    """Admin only: create a notice."""
    supabase = get_supabase()
    row = {
        "title": req.title,
        "content": req.content,
        "pinned": req.pinned,
        "author_email": user["email"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    result = supabase.table("notices").insert(row).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create notice")
    return _row_to_notice(result.data[0])


@router.put("/notices/{notice_id}", response_model=NoticeResponse)
async def update_notice(
    notice_id: str,
    req: NoticeUpdateRequest,
    _user: dict = Depends(require_plan("admin")),
):
    """Admin only: update a notice."""
    supabase = get_supabase()
    update_data: dict = {"updated_at": datetime.now(timezone.utc).isoformat()}
    if req.title is not None:
        update_data["title"] = req.title
    if req.content is not None:
        update_data["content"] = req.content
    if req.pinned is not None:
        update_data["pinned"] = req.pinned

    result = (
        supabase.table("notices")
        .update(update_data)
        .eq("id", notice_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Notice not found")
    return _row_to_notice(result.data[0])


@router.delete("/notices/{notice_id}")
async def delete_notice(
    notice_id: str,
    _user: dict = Depends(require_plan("admin")),
):
    """Admin only: delete a notice."""
    supabase = get_supabase()
    result = (
        supabase.table("notices")
        .delete()
        .eq("id", notice_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Notice not found")
    return {"message": "Notice deleted"}
