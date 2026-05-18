import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Job


async def create_job(db: AsyncSession, document_id: uuid.UUID) -> Job:
    job = Job(document_id=document_id)
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


async def get_job_by_id(db: AsyncSession, job_id: uuid.UUID) -> Job | None:
    result = await db.execute(select(Job).where(Job.id == job_id))
    return result.scalar_one_or_none()


async def get_job_by_document_id(db: AsyncSession, document_id: uuid.UUID) -> Job | None:
    result = await db.execute(select(Job).where(Job.document_id == document_id))
    return result.scalar_one_or_none()


async def update_job_status(
    db: AsyncSession,
    job_id: uuid.UUID,
    status: str,
    error_message: str | None = None,
) -> None:
    job = await get_job_by_id(db, job_id)
    if job:
        job.status = status
        if error_message is not None:
            job.error_message = error_message
        await db.commit()
