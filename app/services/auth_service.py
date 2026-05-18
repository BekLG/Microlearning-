from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.security import create_access_token, verify_telegram_init_data
from app.db.models import User
from app.db.repositories import user_repo


async def authenticate_telegram(
    init_data: str,
    db: AsyncSession,
    settings: Settings,
) -> tuple[User, str]:
    telegram_user = verify_telegram_init_data(init_data, settings)
    user = await user_repo.create_or_update_telegram_user(
        db,
        telegram_id=int(telegram_user["id"]),
        username=telegram_user.get("username"),
        first_name=telegram_user.get("first_name"),
        last_name=telegram_user.get("last_name"),
        photo_url=telegram_user.get("photo_url"),
    )
    token = create_access_token({"sub": str(user.id)}, settings)
    return user, token
