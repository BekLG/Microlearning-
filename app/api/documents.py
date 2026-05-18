import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.db.models import User
from app.schemas.document import DocumentResponse, DocumentStatusResponse, UploadResponse
from app.services import document_service
from app.services.ai_service import AIService
from app.services.storage_service import StorageService

router = APIRouter(prefix="/documents", tags=["documents"])


def get_storage(settings: Settings = Depends(get_settings)) -> StorageService:
    return StorageService(settings)


def get_ai(settings: Settings = Depends(get_settings)) -> AIService:
    return AIService(settings)


@router.post("", status_code=202, response_model=UploadResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    storage: StorageService = Depends(get_storage),
    settings: Settings = Depends(get_settings),
    ai: AIService = Depends(get_ai),
):
    from app.services.processing_service import process_job

    doc = await document_service.upload_document(user, file, db, storage, settings)
    background_tasks.add_task(process_job, doc.id, settings, storage, ai)
    return UploadResponse(document_id=doc.id, status=doc.status)


@router.get("", response_model=list[DocumentResponse])
async def list_documents(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await document_service.get_documents(user, db)


@router.get("/{doc_id}/status", response_model=DocumentStatusResponse)
async def get_status(
    doc_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await document_service.get_document_status(user, doc_id, db)


@router.get("/{doc_id}/lessons")
async def get_lessons(
    doc_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await document_service.get_lessons(user, doc_id, db)
