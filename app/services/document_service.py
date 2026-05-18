import logging
import uuid

from fastapi import HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import ParsingError, StorageError
from app.db.models import Document, User
from app.db.repositories import document_repo, job_repo, lesson_repo
from app.schemas.document import DocumentResponse, DocumentStatusResponse
from app.services.storage_service import StorageService
from app.utils.extractor import count_pages

logger = logging.getLogger(__name__)

# Magic bytes for supported formats
_MAGIC: dict[str, bytes] = {
    "pdf": b"%PDF",
    "pptx": b"PK\x03\x04",
    "docx": b"PK\x03\x04",
}

_ALLOWED_EXTENSIONS = {"pdf", "pptx", "docx"}

# Maximum uncompressed size to prevent zip bombs (100MB)
_MAX_UNCOMPRESSED_SIZE = 100 * 1024 * 1024


def _get_content_limit(ext: str, settings: Settings) -> tuple[int, str]:
    if ext == "pdf":
        return settings.MAX_PDF_PAGES, "pages"
    if ext == "pptx":
        return settings.MAX_PPTX_SLIDES, "slides"
    if ext == "docx":
        return settings.MAX_DOCX_WORDS, "words"
    return settings.MAX_PAGES_PER_DOC, "units"


async def validate_upload(
    file: UploadFile,
    user: User,
    db: AsyncSession,
    settings: Settings,
) -> tuple[str, bytes, int]:
    """Returns (ext, content_bytes, content_units) or raises HTTPException."""
    filename = file.filename or ""
    
    # Sanitize filename to prevent path traversal
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in _ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    content = await file.read()
    
    # Check for empty file
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Empty file not allowed")

    # Magic bytes check to prevent file type spoofing
    expected_magic = _MAGIC.get(ext, b"")
    if expected_magic and not content.startswith(expected_magic):
        raise HTTPException(status_code=400, detail="File content does not match declared type")

    size_mb = len(content) / (1024 * 1024)
    if size_mb > settings.MAX_FILE_SIZE_MB:
        raise HTTPException(status_code=400, detail=f"File exceeds {settings.MAX_FILE_SIZE_MB} MB limit")

    # Validate content size by file type.
    try:
        content_units = count_pages(content, ext)
    except ParsingError:
        raise HTTPException(status_code=400, detail="Invalid or corrupted file")

    limit, unit_label = _get_content_limit(ext, settings)
    if content_units > limit:
        file_label = "DOCX" if ext == "docx" else ext.upper()
        raise HTTPException(
            status_code=400,
            detail=f"{file_label} exceeds {limit} {unit_label} (got {content_units})",
        )

    if content_units == 0:
        raise HTTPException(status_code=400, detail="Document has no content")

    doc_count = await document_repo.count_documents_by_user(db, user.id)
    if doc_count >= settings.FREE_TRIAL_DOCUMENTS:
        raise HTTPException(status_code=403, detail="Free trial document limit reached")

    return ext, content, content_units


async def upload_document(
    user: User,
    file: UploadFile,
    db: AsyncSession,
    storage: StorageService,
    settings: Settings,
) -> Document:
    ext, content, content_units = await validate_upload(file, user, db, settings)

    doc_id = uuid.uuid4()
    try:
        file_url = storage.upload_file(user.id, doc_id, ext, content)
    except StorageError:
        raise HTTPException(status_code=503, detail="Storage service temporarily unavailable")

    doc = await document_repo.create_document(
        db,
        user_id=user.id,
        file_url=file_url,
        file_type=ext,
        page_count=content_units,
    )
    await job_repo.create_job(db, document_id=doc.id)
    return doc


async def get_documents(user: User, db: AsyncSession) -> list[DocumentResponse]:
    docs = await document_repo.get_documents_by_user(db, user.id)
    return [DocumentResponse.model_validate(d) for d in docs]


async def get_document_status(
    user: User, doc_id: uuid.UUID, db: AsyncSession
) -> DocumentStatusResponse:
    doc = await document_repo.get_document_by_id(db, doc_id)
    if not doc or doc.user_id != user.id:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentStatusResponse(status=doc.status)


async def get_lessons(
    user: User, doc_id: uuid.UUID, db: AsyncSession
) -> list[dict]:
    doc = await document_repo.get_document_by_id(db, doc_id)
    if not doc or doc.user_id != user.id:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.status != "completed":
        raise HTTPException(status_code=409, detail="Document processing not complete")
    lessons = await lesson_repo.get_lessons_by_document(db, doc_id)
    return [lesson.content_json for lesson in lessons]
