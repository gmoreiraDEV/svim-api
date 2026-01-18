from __future__ import annotations

from typing import Optional, Tuple
from uuid import UUID

from app.db.pool import get_pool


async def create_user_profile(
    *,
    stack_user_id: Optional[UUID],
    customer_profile: Optional[int],
    name: Optional[str],
    phone: Optional[str],
) -> Tuple[str, Optional[str], Optional[int], Optional[str], Optional[str], str, str]:
    pool = get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                insert into user_profiles (stack_user_id, customer_profile, name, phone)
                values (%s, %s, %s, %s)
                returning
                    id,
                    stack_user_id,
                    customer_profile,
                    name,
                    phone,
                    to_char(created_at at time zone 'utc', 'YYYY-MM-DD"T"HH24:MI:SS"Z"') as created,
                    to_char(updated_at at time zone 'utc', 'YYYY-MM-DD"T"HH24:MI:SS"Z"') as updated
                """,
                (stack_user_id, customer_profile, name, phone),
            )
            row = await cur.fetchone()
            await conn.commit()
            return row


async def update_user_profile(
    *,
    user_id: UUID,
    stack_user_id: Optional[UUID],
    customer_profile: Optional[int],
    name: Optional[str],
    phone: Optional[str],
) -> Optional[Tuple[str, Optional[str], Optional[int], Optional[str], Optional[str], str, str]]:
    pool = get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                update user_profiles
                   set stack_user_id = coalesce(%s, stack_user_id),
                       customer_profile = coalesce(%s, customer_profile),
                       name = coalesce(%s, name),
                       phone = coalesce(%s, phone),
                       updated_at = now()
                 where id = %s
                returning
                    id,
                    stack_user_id,
                    customer_profile,
                    name,
                    phone,
                    to_char(created_at at time zone 'utc', 'YYYY-MM-DD"T"HH24:MI:SS"Z"') as created,
                    to_char(updated_at at time zone 'utc', 'YYYY-MM-DD"T"HH24:MI:SS"Z"') as updated
                """,
                (stack_user_id, customer_profile, name, phone, str(user_id)),
            )
            row = await cur.fetchone()
            await conn.commit()
            return row if row else None


async def get_user_profile_by_id(user_id: UUID) -> Optional[Tuple[str, Optional[str], Optional[int], Optional[str], Optional[str], str, str]]:
    pool = get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                select id,
                       stack_user_id,
                       customer_profile,
                       name,
                       phone,
                       to_char(created_at at time zone 'utc', 'YYYY-MM-DD"T"HH24:MI:SS"Z"') as created,
                       to_char(updated_at at time zone 'utc', 'YYYY-MM-DD"T"HH24:MI:SS"Z"') as updated
                  from user_profiles
                 where id = %s
                """,
                (str(user_id),),
            )
            row = await cur.fetchone()
            return row if row else None


async def get_user_profile_by_stack_user_id(
    stack_user_id: UUID,
) -> Optional[Tuple[str, Optional[str], Optional[int], Optional[str], Optional[str], str, str]]:
    pool = get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                select id,
                       stack_user_id,
                       customer_profile,
                       name,
                       phone,
                       to_char(created_at at time zone 'utc', 'YYYY-MM-DD"T"HH24:MI:SS"Z"') as created,
                       to_char(updated_at at time zone 'utc', 'YYYY-MM-DD"T"HH24:MI:SS"Z"') as updated
                  from user_profiles
                 where stack_user_id = %s
                """,
                (str(stack_user_id),),
            )
            row = await cur.fetchone()
            return row if row else None


async def get_user_profile_by_customer_profile(
    customer_profile: int,
) -> Optional[Tuple[str, Optional[str], Optional[int], Optional[str], Optional[str], str, str]]:
    pool = get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                select id,
                       stack_user_id,
                       customer_profile,
                       name,
                       phone,
                       to_char(created_at at time zone 'utc', 'YYYY-MM-DD"T"HH24:MI:SS"Z"') as created,
                       to_char(updated_at at time zone 'utc', 'YYYY-MM-DD"T"HH24:MI:SS"Z"') as updated
                  from user_profiles
                 where customer_profile = %s
                """,
                (customer_profile,),
            )
            row = await cur.fetchone()
            return row if row else None
