import asyncio
import json
import logging
import re
from typing import Any

import httpx

from app.core.config import Settings
from app.core.exceptions import AIProviderUnavailableError, AIServiceError
from app.prompts.lesson_prompt import (
    build_facts_prompt,
    build_mcqs_from_facts_prompt,
    build_overview_facts_prompt,
    build_overview_mcqs_from_facts_prompt,
)

logger = logging.getLogger(__name__)


def _parse_model_list(primary_model: str, fallback_models: str) -> list[str]:
    models = [primary_model]
    models.extend(model.strip() for model in fallback_models.split(",") if model.strip())
    return list(dict.fromkeys(models))


def _is_retryable_http_error(error: httpx.HTTPStatusError) -> bool:
    status_code = error.response.status_code
    return status_code == 429 or 500 <= status_code < 600


async def _sleep_for_rate_limit(
    error: httpx.HTTPStatusError,
    attempt: int,
    max_wait_seconds: int,
) -> None:
    retry_after = error.response.headers.get("Retry-After")
    if retry_after:
        try:
            delay = min(float(retry_after), float(max_wait_seconds))
        except ValueError:
            delay = min(float(2 ** attempt), float(max_wait_seconds))
    else:
        delay = min(float(2 ** attempt), float(max_wait_seconds))

    logger.warning(
        "OpenRouter rate-limited request; waiting %.2fs before retry. retry_after=%s",
        delay,
        retry_after,
    )
    await asyncio.sleep(delay)


class AIService:
    def __init__(self, settings: Settings) -> None:
        headers = {"Authorization": f"Bearer {settings.OPENROUTER_API_KEY}"}
        if settings.OPENROUTER_SITE_URL:
            headers["HTTP-Referer"] = settings.OPENROUTER_SITE_URL
        if settings.OPENROUTER_APP_NAME:
            headers["X-Title"] = settings.OPENROUTER_APP_NAME

        self._client = httpx.AsyncClient(
            base_url="https://openrouter.ai/api/v1",
            headers=headers,
        )
        self._models = _parse_model_list(settings.OPENROUTER_MODEL, settings.OPENROUTER_FALLBACK_MODELS)
        self._timeout = settings.AI_TIMEOUT_SECONDS
        self._max_retries = settings.MAX_RETRIES
        self._max_429_wait_seconds = settings.OPENROUTER_MAX_429_WAIT_SECONDS

    async def health_check(self) -> None:
        try:
            response = await asyncio.wait_for(self._client.get("/models"), timeout=10)
            response.raise_for_status()
        except Exception as e:
            raise AIProviderUnavailableError(f"OpenRouter not reachable: {e}") from e

    async def generate_facts(self, chunk: str, min_facts: int, max_facts: int) -> list[dict]:
        prompt = build_facts_prompt(chunk, min_facts, max_facts)
        last_error: Exception | None = None

        for model in self._models:
            logger.info("Trying OpenRouter model '%s' for fact generation with chunk of %s chars", model, len(chunk))
            try:
                response = await self._call_model_with_retry(model, prompt)
                items = self._parse_response(response)
                facts = _validate_fact_items(items)
                if len(facts) < min_facts:
                    raise AIServiceError(
                        f"Model '{model}' returned too few facts: {len(facts)}/{min_facts}"
                    )
                return facts[:max_facts]
            except AIServiceError as error:
                last_error = error
                logger.warning("Fact model '%s' failed: %s", model, error)
                continue

        raise AIServiceError(f"All OpenRouter models failed for fact generation. Last error: {last_error}") from last_error

    async def generate_mcqs_from_facts(self, facts: list[dict], mcq_count: int) -> list[dict]:
        prompt = build_mcqs_from_facts_prompt(facts, mcq_count)
        last_error: Exception | None = None

        for model in self._models:
            logger.info("Trying OpenRouter model '%s' for MCQ generation from %s facts", model, len(facts))
            try:
                response = await self._call_model_with_retry(model, prompt)
                items = self._parse_response(response)
                return _validate_mcq_items_with_support(items, facts)
            except AIServiceError as error:
                last_error = error
                logger.warning("MCQ model '%s' failed: %s", model, error)
                continue

        raise AIServiceError(f"All OpenRouter models failed for MCQ generation. Last error: {last_error}") from last_error

    async def generate_overview_facts(self, text_excerpt: str, min_facts: int, max_facts: int) -> list[dict]:
        prompt = build_overview_facts_prompt(text_excerpt, min_facts, max_facts)
        last_error: Exception | None = None

        for model in self._models:
            logger.info("Trying OpenRouter model '%s' for overview fact generation", model)
            try:
                response = await self._call_model_with_retry(model, prompt)
                items = self._parse_response(response)
                facts = _validate_fact_items(items)
                if len(facts) < min_facts:
                    raise AIServiceError(
                        f"Model '{model}' returned too few overview facts: {len(facts)}/{min_facts}"
                    )
                return facts[:max_facts]
            except AIServiceError as error:
                last_error = error
                logger.warning("Overview fact model '%s' failed: %s", model, error)
                continue

        raise AIServiceError(f"All OpenRouter models failed for overview facts. Last error: {last_error}") from last_error

    async def generate_overview_mcqs_from_facts(self, facts: list[dict], mcq_count: int) -> list[dict]:
        prompt = build_overview_mcqs_from_facts_prompt(facts, mcq_count)
        last_error: Exception | None = None

        for model in self._models:
            logger.info("Trying OpenRouter model '%s' for overview MCQ generation", model)
            try:
                response = await self._call_model_with_retry(model, prompt)
                items = self._parse_response(response)
                return _validate_mcq_items_with_support(items, facts)
            except AIServiceError as error:
                last_error = error
                logger.warning("Overview MCQ model '%s' failed: %s", model, error)
                continue

        raise AIServiceError(f"All OpenRouter models failed for overview MCQs. Last error: {last_error}") from last_error

    async def _call_model_with_retry(self, model: str, prompt: str) -> httpx.Response:
        last_error: Exception | None = None

        for attempt in range(self._max_retries + 1):
            try:
                response = await asyncio.wait_for(
                    self._client.post(
                        "/chat/completions",
                        json={
                            "model": model,
                            "messages": [
                                {"role": "system", "content": "Return only the requested JSON array."},
                                {"role": "user", "content": prompt},
                            ],
                            "temperature": 0.2,
                            "stream": False,
                        },
                    ),
                    timeout=self._timeout,
                )
                response.raise_for_status()
                return response
            except httpx.HTTPStatusError as error:
                last_error = error
                status_code = error.response.status_code
                logger.warning(
                    "OpenRouter model '%s' returned HTTP %s on attempt %s/%s",
                    model,
                    status_code,
                    attempt + 1,
                    self._max_retries + 1,
                )
                if status_code in (400, 401, 403):
                    raise AIServiceError(
                        f"OpenRouter request failed for model '{model}' with HTTP {status_code}"
                    ) from error
                if status_code == 429 and attempt < self._max_retries:
                    await _sleep_for_rate_limit(error, attempt, self._max_429_wait_seconds)
                    continue
                if _is_retryable_http_error(error) and attempt < self._max_retries:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise AIServiceError(
                    f"OpenRouter request failed for model '{model}' with HTTP {status_code}"
                ) from error
            except Exception as error:
                last_error = error
                if attempt < self._max_retries:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise AIServiceError(
                    f"Exhausted {self._max_retries + 1} attempts for model '{model}': {error}"
                ) from error

        raise AIServiceError(f"Exhausted {self._max_retries + 1} attempts for model '{model}': {last_error}") from last_error

    def _parse_response(self, response: httpx.Response) -> list[dict]:
        payload = response.json()
        raw = payload["choices"][0]["message"]["content"].strip()
        logger.info("OpenRouter response: %s chars", len(raw))
        if payload.get("usage"):
            logger.info("OpenRouter usage: %s", payload["usage"])

        match = re.search(r"\[.*\]", raw, re.DOTALL)
        if not match:
            logger.error("AI response missing JSON array. Response: %s", raw[:500])
            raise AIServiceError("AI response did not contain a JSON array")

        try:
            items: list[dict] = json.loads(match.group())
            logger.info("Parsed %s lesson items", len(items))
        except json.JSONDecodeError as e:
            logger.error("Failed to parse AI JSON response: %s", e)
            raise AIServiceError(f"Failed to parse AI response as JSON: {e}") from e

        return items


def _validate_fact_items(items: list[dict]) -> list[dict]:
    validated: list[dict] = []
    for item in items:
        item_type = item.get("type")
        if item_type != "fact":
            raise AIServiceError(f"Unsupported fact item type: {item_type}")

        text = item.get("text")
        if not isinstance(text, str) or not text.strip():
            raise AIServiceError("Fact items must include non-empty text")

        validated.append({"type": "fact", "text": text.strip()})

    return validated


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().lower()


def _validate_mcq_items_with_support(items: list[dict], facts: list[dict]) -> list[dict]:
    validated: list[dict] = []
    normalized_facts = [_normalize_text(fact["text"]) for fact in facts]

    for item in items:
        item_type = item.get("type")
        if item_type != "mcq":
            raise AIServiceError(f"Unsupported MCQ item type: {item_type}")

        question = item.get("question")
        options = item.get("options")
        answer = item.get("answer")
        explanation = item.get("explanation")
        supporting_fact_indexes = item.get("supporting_fact_indexes")

        if not isinstance(question, str) or not question.strip():
            raise AIServiceError("MCQ items must include a question")
        if not isinstance(options, list) or len(options) != 4 or not all(isinstance(opt, str) and opt.strip() for opt in options):
            raise AIServiceError("MCQ items must contain exactly 4 non-empty options")
        if not isinstance(answer, str) or answer not in options:
            raise AIServiceError("MCQ answer must match one of the options")
        if not isinstance(explanation, str) or not explanation.strip():
            raise AIServiceError("MCQ items must include an explanation")
        if not isinstance(supporting_fact_indexes, list) or not supporting_fact_indexes:
            raise AIServiceError("MCQ items must include at least one supporting fact index")
        if not all(isinstance(idx, int) for idx in supporting_fact_indexes):
            raise AIServiceError("supporting_fact_indexes must be integers")
        if not all(0 <= idx < len(facts) for idx in supporting_fact_indexes):
            raise AIServiceError("supporting_fact_indexes contain out-of-range values")

        normalized_answer = _normalize_text(answer)
        if not any(normalized_answer in normalized_facts[idx] for idx in supporting_fact_indexes):
            raise AIServiceError("MCQ answer is not supported by the referenced facts")

        validated.append(
            {
                "type": "mcq",
                "question": question.strip(),
                "options": [opt.strip() for opt in options],
                "answer": answer,
                "explanation": explanation.strip(),
            }
        )

    return validated
