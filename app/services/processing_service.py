import logging
import traceback
import uuid

from app.core.config import Settings
from app.db.base import AsyncSessionLocal
from app.db.repositories import document_repo, job_repo, lesson_repo
from app.services.ai_service import AIService
from app.services.storage_service import StorageService
from app.utils.extractor import extract_text
from app.utils.text_pipeline import chunk_text, clean_text

logger = logging.getLogger(__name__)

_OVERVIEW_MIN_FACTS = 12
_OVERVIEW_MAX_FACTS = 15
_OVERVIEW_MCQS = 3
_TARGET_TOTAL_ITEMS_SOFT_CAP = 110


def _clamp(value: int, lower: int, upper: int) -> int:
    return max(lower, min(value, upper))


def _compute_fact_range(chunk: str) -> tuple[int, int]:
    words = len(chunk.split())
    min_facts = _clamp(round(words / 350), 6, 10)
    max_facts = _clamp(round(words / 220), 10, 18)
    if max_facts < min_facts:
        max_facts = min_facts
    return min_facts, max_facts


def _compute_mcq_count(fact_count: int) -> int:
    return _clamp(fact_count // 4, 1, 3)


async def process_job(
    document_id: uuid.UUID,
    settings: Settings,
    storage: StorageService,
    ai: AIService,
) -> None:
    async with AsyncSessionLocal() as db:
        doc = await document_repo.get_document_by_id(db, document_id)
        if not doc or doc.status in ("completed", "failed"):
            return

        job = await job_repo.get_job_by_document_id(db, document_id)
        if not job:
            return

        await document_repo.update_document_status(db, document_id, "processing")
        await job_repo.update_job_status(db, job.id, "processing")
        logger.info("Starting processing for document %s", document_id)

        try:
            logger.info("Downloading file from storage: %s", doc.file_url)
            file_bytes = storage.download_file(doc.file_url)
            logger.info("Downloaded %s bytes", len(file_bytes))

            logger.info("Extracting text from %s", doc.file_type)
            raw_text = extract_text(file_bytes, doc.file_type)
            logger.info("Extracted %s chars of text", len(raw_text))

            logger.info("Cleaning text")
            cleaned = clean_text(raw_text)
            logger.info("Cleaned text: %s chars", len(cleaned))

            overview_source = cleaned[: min(len(cleaned), settings.MAX_CHARS_PER_CHUNK * 4)]
            logger.info("Generating overview facts from %s chars of cleaned text", len(overview_source))
            overview_facts = await ai.generate_overview_facts(
                overview_source,
                _OVERVIEW_MIN_FACTS,
                _OVERVIEW_MAX_FACTS,
            )
            overview_mcqs = await ai.generate_overview_mcqs_from_facts(overview_facts, _OVERVIEW_MCQS)
            lesson_items = overview_facts + overview_mcqs
            logger.info(
                "Generated %s overview facts and %s overview MCQs",
                len(overview_facts),
                len(overview_mcqs),
            )

            logger.info(
                "Chunking text into max %s chunks with %s chars per chunk",
                settings.MAX_CHUNKS,
                settings.MAX_CHARS_PER_CHUNK,
            )
            chunks = chunk_text(cleaned, settings.MAX_CHUNKS, settings.MAX_CHARS_PER_CHUNK)
            logger.info("Created %s chunks", len(chunks))

            for i, chunk in enumerate(chunks):
                if len(lesson_items) >= _TARGET_TOTAL_ITEMS_SOFT_CAP:
                    logger.info(
                        "Reached soft cap of %s total items; stopping chunk processing",
                        _TARGET_TOTAL_ITEMS_SOFT_CAP,
                    )
                    break

                min_facts, max_facts = _compute_fact_range(chunk)
                logger.info("Processing chunk %s/%s", i + 1, len(chunks))
                logger.info("Chunk fact target range: min_facts=%s max_facts=%s", min_facts, max_facts)
                facts = await ai.generate_facts(chunk, min_facts, max_facts)
                mcq_count = _compute_mcq_count(len(facts))
                mcqs = await ai.generate_mcqs_from_facts(facts, mcq_count)
                logger.info(
                    "Generated %s facts and %s MCQs from chunk %s",
                    len(facts),
                    len(mcqs),
                    i + 1,
                )
                lesson_items.extend(facts)
                lesson_items.extend(mcqs)

            logger.info("Inserting %s lessons into database", len(lesson_items))
            await lesson_repo.insert_lessons(db, document_id, lesson_items)
            await document_repo.update_document_status(db, document_id, "completed")
            await job_repo.update_job_status(db, job.id, "completed")
            logger.info("Successfully completed processing for document %s", document_id)

        except Exception as e:
            error_detail = str(e)
            full_traceback = traceback.format_exc()
            logger.error("Processing failed for document %s: %s", document_id, error_detail)
            logger.error("Full traceback: %s", full_traceback)
            await document_repo.update_document_status(db, document_id, "failed")
            await job_repo.update_job_status(db, job.id, "failed", error_message=error_detail)
