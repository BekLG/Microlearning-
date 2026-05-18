import uuid
from datetime import datetime
from typing import Annotated, Literal, Union

from pydantic import BaseModel


class DocumentResponse(BaseModel):
    id: uuid.UUID
    file_type: str
    status: str
    page_count: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


class UploadResponse(BaseModel):
    document_id: uuid.UUID
    status: str


class DocumentStatusResponse(BaseModel):
    status: str


class FactItem(BaseModel):
    type: Literal["fact"]
    text: str


class MCQItem(BaseModel):
    type: Literal["mcq"]
    question: str
    options: list[str]
    answer: str
    explanation: str


LessonItem = Annotated[Union[FactItem, MCQItem], ...]
