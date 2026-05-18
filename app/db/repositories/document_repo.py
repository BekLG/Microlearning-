import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Document


async def create_document(
    db: AsyncSession,
    user_id: uuid.UUID,
    file_url: str,
    file_type: str,
    page_count: int | None = None,
) -> Document:
    doc = Document(user_id=user_id, file_url=file_url, file_type=file_type, page_count=page_count)
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return doc


async def get_documents_by_user(db: AsyncSession, user_id: uuid.UUID) -> list[Document]:
    result = await db.execute(
        select(Document).where(Document.user_id == user_id).order_by(Document.created_at.desc())
    )
    return list(result.scalars().all())


async def get_document_by_id(db: AsyncSession, doc_id: uuid.UUID) -> Document | None:
    result = await db.execute(select(Document).where(Document.id == doc_id))
    return result.scalar_one_or_none()


async def update_document_status(
    db: AsyncSession, doc_id: uuid.UUID, status: str
) -> None:
    doc = await get_document_by_id(db, doc_id)
    if doc:
        doc.status = status
        await db.commit()


async def count_documents_by_user(db: AsyncSession, user_id: uuid.UUID) -> int:
    result = await db.execute(
        select(func.count()).select_from(Document).where(Document.user_id == user_id)
    )
    return result.scalar_one()
