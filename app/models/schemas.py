from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class DocumentType(str, Enum):
    PATENT = "patent"
    RESEARCH_PAPER = "research_paper"


class ClassificationStatus(str, Enum):
    PENDING = "pending"
    AGREED = "agreed"
    DISAGREED = "disagreed"
    HUMAN_REVIEWED = "human_reviewed"


class Classification(BaseModel):
    category: str
    subcategory: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0)
    keywords: list[str] = []


class AIClassificationResult(BaseModel):
    model_name: str
    classification: Classification
    reasoning: str


class Document(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    abstract: str
    doc_type: DocumentType
    source: Optional[str] = None
    authors: list[str] = []
    year: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    gpt_classification: Optional[AIClassificationResult] = None
    claude_classification: Optional[AIClassificationResult] = None

    status: ClassificationStatus = ClassificationStatus.PENDING
    final_classification: Optional[Classification] = None
    human_review_note: Optional[str] = None


class DocumentCreate(BaseModel):
    title: str
    abstract: str
    doc_type: DocumentType
    source: Optional[str] = None
    authors: list[str] = []
    year: Optional[int] = None


class HumanReviewRequest(BaseModel):
    document_id: str
    chosen_classification: Classification
    note: Optional[str] = None


class ClassifyRequest(BaseModel):
    document_ids: Optional[list[str]] = None


class GraphSettings(BaseModel):
    show_categories: bool = True
    show_keywords: bool = False
    height: str = "800px"
    width: str = "100%"
