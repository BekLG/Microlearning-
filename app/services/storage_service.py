import io
import uuid

import cloudinary
import cloudinary.api
import cloudinary.uploader
import httpx

from app.core.config import Settings
from app.core.exceptions import StorageError


class StorageService:
    def __init__(self, settings: Settings) -> None:
        cloudinary.config(
            cloud_name=settings.CLOUDINARY_CLOUD_NAME,
            api_key=settings.CLOUDINARY_API_KEY,
            api_secret=settings.CLOUDINARY_API_SECRET,
            secure=True,
        )

    def ensure_bucket(self) -> None:
        try:
            cloudinary.api.ping()
        except Exception as e:
            raise StorageError(f"Cloudinary unavailable: {e}") from e

    def upload_file(
        self,
        user_id: uuid.UUID,
        doc_id: uuid.UUID,
        ext: str,
        data: bytes,
    ) -> str:
        object_key = f"documents/{user_id}/{doc_id}.{ext}"
        try:
            file_obj = io.BytesIO(data)
            file_obj.name = f"{doc_id}.{ext}"
            upload = cloudinary.uploader.upload(
                file_obj,
                resource_type="raw",
                public_id=object_key,
                overwrite=True,
            )
        except Exception as e:
            raise StorageError(f"Upload failed: {e}") from e
        return upload["secure_url"]

    def download_file(self, object_key: str) -> bytes:
        try:
            response = httpx.get(object_key, timeout=30)
            response.raise_for_status()
            return response.content
        except Exception as e:
            raise StorageError(f"Download failed: {e}") from e
