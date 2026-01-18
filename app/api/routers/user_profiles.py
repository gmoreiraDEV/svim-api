from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.db.threads import list_threads_by_user_id, update_thread_user_id
from app.db.user_profiles import (
    create_user_profile,
    get_user_profile_by_customer_profile,
    get_user_profile_by_id,
    get_user_profile_by_stack_user_id,
    update_user_profile,
)
from app.models.schemas import ThreadObj, UserProfileCreate, UserProfileObj, UserProfileThreadUpdate


router = APIRouter(tags=["user_profiles"])


def _row_to_obj(row) -> UserProfileObj:
    user_id, stack_user_id, customer_profile, name, phone, created_at, updated_at = row
    return UserProfileObj(
        id=user_id,
        stack_user_id=stack_user_id,
        customer_profile=customer_profile,
        name=name,
        phone=phone,
        created_at=created_at,
        updated_at=updated_at,
    )


@router.post("/user-profiles", response_model=UserProfileObj)
async def create_user_profile(body: UserProfileCreate) -> UserProfileObj:
    if body.stack_user_id is None and body.customer_profile is None:
        raise HTTPException(status_code=400, detail="stack_user_id ou customer_profile é obrigatório")

    by_stack = None
    by_customer = None
    if body.stack_user_id is not None:
        by_stack = await get_user_profile_by_stack_user_id(body.stack_user_id)
    if body.customer_profile is not None:
        by_customer = await get_user_profile_by_customer_profile(body.customer_profile)

    if by_stack and by_customer and by_stack[0] != by_customer[0]:
        raise HTTPException(status_code=409, detail="stack_user_id e customer_profile pertencem a usuários diferentes")

    existing = by_stack or by_customer
    if existing:
        updated = await update_user_profile(
            user_id=UUID(existing[0]),
            stack_user_id=body.stack_user_id,
            customer_profile=body.customer_profile,
            name=body.name,
            phone=body.phone,
        )
        if not updated:
            raise HTTPException(status_code=500, detail="Failed to update user profile")
        return _row_to_obj(updated)

    row = await create_user_profile(
        stack_user_id=body.stack_user_id,
        customer_profile=body.customer_profile,
        name=body.name,
        phone=body.phone,
    )
    return _row_to_obj(row)


@router.get("/user-profiles/by-provider-id", response_model=UserProfileObj)
async def read_user_profile_by_provider_id(
    stack_user_id: UUID | None = None,
    customer_profile: int | None = None,
) -> UserProfileObj:
    if stack_user_id is None and customer_profile is None:
        raise HTTPException(status_code=400, detail="stack_user_id ou customer_profile é obrigatório")

    by_stack = None
    by_customer = None
    if stack_user_id is not None:
        by_stack = await get_user_profile_by_stack_user_id(stack_user_id)
    if customer_profile is not None:
        by_customer = await get_user_profile_by_customer_profile(customer_profile)

    if by_stack and by_customer and by_stack[0] != by_customer[0]:
        raise HTTPException(status_code=409, detail="stack_user_id e customer_profile pertencem a usuários diferentes")

    row = by_stack or by_customer
    if not row:
        raise HTTPException(status_code=404, detail="User profile not found")

    return _row_to_obj(row)


@router.get("/user-profiles/{user_id}", response_model=UserProfileObj)
async def read_user_profile(user_id: UUID) -> UserProfileObj:
    row = await get_user_profile_by_id(user_id)
    if not row:
        raise HTTPException(status_code=404, detail="User profile not found")
    return _row_to_obj(row)


@router.patch("/user-profiles/{user_id}/thread", response_model=UserProfileObj)
async def update_user_profile_thread(
    user_id: UUID,
    body: UserProfileThreadUpdate,
) -> UserProfileObj:
    row = await get_user_profile_by_id(user_id)
    if not row:
        raise HTTPException(status_code=404, detail="User profile not found")

    updated = await update_thread_user_id(body.thread_id, user_id)
    if not updated:
        raise HTTPException(status_code=404, detail="Thread not found")

    return _row_to_obj(row)


@router.get("/user-profiles/{user_id}/threads")
async def list_user_profile_threads(
    user_id: UUID,
    limit: int = 50,
) -> list[ThreadObj]:
    row = await get_user_profile_by_id(user_id)
    if not row:
        raise HTTPException(status_code=404, detail="User profile not found")

    rows = await list_threads_by_user_id(user_id, limit=limit)
    return [ThreadObj(thread_id=t, created_at=ts, values={"messages": []}) for t, ts in rows]
