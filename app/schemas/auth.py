import uuid

from pydantic import BaseModel


class TelegramAuthRequest(BaseModel):
    init_data: str


class AuthUserResponse(BaseModel):
    id: uuid.UUID
    telegram_id: int
    username: str | None
    first_name: str | None
    last_name: str | None
    photo_url: str | None


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: AuthUserResponse
