from __future__ import annotations

from typing import Optional, Tuple

from app.db.pool import get_pool


async def upsert_user_profile(
    *,
    customer_profile: int,
    name: Optional[str],
    phone: Optional[str],
) -> None:
    pool = get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                insert into user_profiles (customer_profile, name, phone)
                values (%s, %s, %s)
                on conflict (customer_profile)
                do update set
                    name = excluded.name,
                    phone = excluded.phone,
                    updated_at = now()
                """,
                (customer_profile, name, phone),
            )
            await conn.commit()


async def get_user_profile(customer_profile: int) -> Optional[Tuple[int, Optional[str], Optional[str], str, str]]:
    pool = get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                select customer_profile,
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
