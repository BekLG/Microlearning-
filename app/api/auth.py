from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.base import get_db
from app.schemas.auth import AuthUserResponse, LoginResponse, TelegramAuthRequest
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/telegram", response_model=LoginResponse)
async def authenticate_telegram(
    body: TelegramAuthRequest,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    user, token = await auth_service.authenticate_telegram(body.init_data, db, settings)
    return LoginResponse(
        access_token=token,
        user=AuthUserResponse(
            id=user.id,
            telegram_id=user.telegram_id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            photo_url=user.photo_url,
        ),
    )
