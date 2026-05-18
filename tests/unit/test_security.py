import hashlib
import hmac
import json
from datetime import datetime, timezone
from urllib.parse import urlencode

import pytest
from jose import jwt

from app.core.config import Settings
from app.core.security import (
    ALGORITHM,
    create_access_token,
    verify_telegram_init_data,
)


_test_settings = Settings(
    APP_ENV="test",
    FREE_TRIAL_DOCUMENTS=3,
    MAX_FILE_SIZE_MB=10,
    MAX_PAGES_PER_DOC=50,
    MAX_CHUNKS=20,
    FACTS_PER_CHUNK=5,
    MCQ_INTERVAL=3,
    AI_TIMEOUT_SECONDS=60,
    MAX_RETRIES=3,
    OPENROUTER_API_KEY="test-openrouter-key",
    OPENROUTER_MODEL="google/gemma-4-31b-it:free",
    OPENROUTER_SITE_URL="https://example.com",
    OPENROUTER_APP_NAME="Microlearn AI",
    SECRET_KEY="test-secret-key-with-32-characters!!",
    DATABASE_URL="postgresql+asyncpg://user:pass@localhost/test",
    CLOUDINARY_CLOUD_NAME="cloud",
    CLOUDINARY_API_KEY="key",
    CLOUDINARY_API_SECRET="secret",
    TELEGRAM_BOT_TOKEN="telegram-bot-token",
)


def _build_init_data(user: dict, auth_timestamp: int | None = None) -> str:
    auth_timestamp = auth_timestamp or int(datetime.now(timezone.utc).timestamp())
    payload = {
        "auth_date": str(auth_timestamp),
        "query_id": "AAEAAAE",
        "user": json.dumps(user, separators=(",", ":")),
    }
    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(payload.items()))
    secret_key = hmac.new(
        b"WebAppData",
        _test_settings.TELEGRAM_BOT_TOKEN.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    payload["hash"] = hmac.new(
        secret_key,
        data_check_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return urlencode(payload)


def test_jwt_uses_hs256_algorithm():
    payload = {"sub": "550e8400-e29b-41d4-a716-446655440000", "role": "user"}
    token = create_access_token(payload, _test_settings)

    header = jwt.get_unverified_header(token)
    assert header["alg"] == ALGORITHM == "HS256"

    decoded = jwt.decode(token, _test_settings.SECRET_KEY, algorithms=[ALGORITHM])
    assert decoded["sub"] == payload["sub"]
    assert decoded["role"] == payload["role"]


def test_verify_telegram_init_data_accepts_valid_payload():
    init_data = _build_init_data(
        {
            "id": 123456789,
            "username": "microlearn_user",
            "first_name": "Bek",
        }
    )

    user = verify_telegram_init_data(init_data, _test_settings)
    assert user["id"] == 123456789
    assert user["username"] == "microlearn_user"


def test_verify_telegram_init_data_rejects_invalid_hash():
    init_data = _build_init_data({"id": 123456789, "first_name": "Bek"})
    tampered = init_data.replace("hash=", "hash=bad")

    with pytest.raises(Exception):
        verify_telegram_init_data(tampered, _test_settings)
