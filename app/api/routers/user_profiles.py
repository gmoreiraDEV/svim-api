from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.db.threads import list_threads_by_customer_profile, update_thread_customer_profile
from app.db.user_profiles import get_user_profile, upsert_user_profile
from app.models.schemas import ThreadObj, UserProfileCreate, UserProfileObj, UserProfileThreadUpdate


router = APIRouter(tags=["user_profiles"])


@router.post("/user-profiles", response_model=UserProfileObj)
async def create_user_profile(body: UserProfileCreate) -> UserProfileObj:
    await upsert_user_profile(
        customer_profile=body.customer_profile,
        name=body.name,
        phone=body.phone,
    )

    row = await get_user_profile(body.customer_profile)
    if not row:
        raise HTTPException(status_code=500, detail="Failed to create user profile")

    customer_profile, name, phone, created_at, updated_at = row
    return UserProfileObj(
        customer_profile=customer_profile,
        name=name,
        phone=phone,
        created_at=created_at,
        updated_at=updated_at,
    )


@router.get("/user-profiles/{customer_profile}", response_model=UserProfileObj)
async def read_user_profile(customer_profile: int) -> UserProfileObj:
    row = await get_user_profile(customer_profile)
    if not row:
        raise HTTPException(status_code=404, detail="User profile not found")

    customer_profile, name, phone, created_at, updated_at = row
    return UserProfileObj(
        customer_profile=customer_profile,
        name=name,
        phone=phone,
        created_at=created_at,
        updated_at=updated_at,
    )


@router.patch("/user-profiles/{customer_profile}/thread", response_model=UserProfileObj)
async def update_user_profile_thread(
    customer_profile: int,
    body: UserProfileThreadUpdate,
) -> UserProfileObj:
    row = await get_user_profile(customer_profile)
    if not row:
        raise HTTPException(status_code=404, detail="User profile not found")

    updated = await update_thread_customer_profile(body.thread_id, customer_profile)
    if not updated:
        raise HTTPException(status_code=404, detail="Thread not found")

    customer_profile, name, phone, created_at, updated_at = row
    return UserProfileObj(
        customer_profile=customer_profile,
        name=name,
        phone=phone,
        created_at=created_at,
        updated_at=updated_at,
    )


@router.get("/user-profiles/{customer_profile}/threads")
async def list_user_profile_threads(
    customer_profile: int,
    limit: int = 50,
) -> list[ThreadObj]:
    row = await get_user_profile(customer_profile)
    if not row:
        raise HTTPException(status_code=404, detail="User profile not found")

    rows = await list_threads_by_customer_profile(customer_profile, limit=limit)
    return [ThreadObj(thread_id=t, created_at=ts, values={"messages": []}) for t, ts in rows]
