import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User


async def create_or_update_telegram_user(
    db: AsyncSession,
    telegram_id: int,
    username: str | None,
    first_name: str | None,
    last_name: str | None,
    photo_url: str | None,
) -> User:
    user = await get_user_by_telegram_id(db, telegram_id)
    if user:
        user.username = username
        user.first_name = first_name
        user.last_name = last_name
        user.photo_url = photo_url
        await db.commit()
        await db.refresh(user)
        return user

    user = User(
        telegram_id=telegram_id,
        username=username,
        first_name=first_name,
        last_name=last_name,
        photo_url=photo_url,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def get_user_by_telegram_id(db: AsyncSession, telegram_id: int) -> User | None:
    result = await db.execute(select(User).where(User.telegram_id == telegram_id))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()
