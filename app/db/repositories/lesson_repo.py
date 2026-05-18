import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Lesson


async def insert_lessons(
    db: AsyncSession, document_id: uuid.UUID, items: list[dict]
) -> None:
    lessons = [Lesson(document_id=document_id, content_json=item) for item in items]
    db.add_all(lessons)
    await db.commit()


async def get_lessons_by_document(
    db: AsyncSession, document_id: uuid.UUID
) -> list[Lesson]:
    result = await db.execute(
        select(Lesson)
        .where(Lesson.document_id == document_id)
        .order_by(Lesson.created_at.asc())
    )
    return list(result.scalars().all())
