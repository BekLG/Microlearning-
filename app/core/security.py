import hashlib
import hmac
import json
from urllib.parse import parse_qsl
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from jose import JWTError, jwt

from app.core.config import Settings

ALGORITHM = "HS256"


def create_access_token(data: dict, settings: Settings) -> str:
    payload = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload["exp"] = expire
    payload["iat"] = datetime.now(timezone.utc)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str, settings: Settings) -> dict:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        if "sub" not in payload:
            raise HTTPException(status_code=401, detail="Invalid token structure")
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def parse_telegram_init_data(init_data: str) -> dict[str, str]:
    try:
        parsed = dict(parse_qsl(init_data, keep_blank_values=True, strict_parsing=True))
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Invalid Telegram init data") from exc
    if not parsed:
        raise HTTPException(status_code=401, detail="Missing Telegram init data")
    return parsed


def verify_telegram_init_data(init_data: str, settings: Settings) -> dict:
    parsed = parse_telegram_init_data(init_data)
    received_hash = parsed.pop("hash", None)
    if not received_hash:
        raise HTTPException(status_code=401, detail="Telegram signature missing")

    data_check_string = "\n".join(
        f"{key}={value}" for key, value in sorted(parsed.items())
    )
    secret_key = hmac.new(
        b"WebAppData",
        settings.TELEGRAM_BOT_TOKEN.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    computed_hash = hmac.new(
        secret_key,
        data_check_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(computed_hash, received_hash):
        raise HTTPException(status_code=401, detail="Invalid Telegram signature")

    auth_date_raw = parsed.get("auth_date")
    if not auth_date_raw:
        raise HTTPException(status_code=401, detail="Telegram auth date missing")

    try:
        auth_date = datetime.fromtimestamp(int(auth_date_raw), tz=timezone.utc)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Invalid Telegram auth date") from exc

    age = (datetime.now(timezone.utc) - auth_date).total_seconds()
    if age > settings.TELEGRAM_INITDATA_MAX_AGE_SECONDS:
        raise HTTPException(status_code=401, detail="Telegram auth data expired")

    user_raw = parsed.get("user")
    if not user_raw:
        raise HTTPException(status_code=401, detail="Telegram user missing")

    try:
        user = json.loads(user_raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=401, detail="Invalid Telegram user payload") from exc

    if "id" not in user:
        raise HTTPException(status_code=401, detail="Telegram user id missing")

    return user
