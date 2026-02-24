import json
import asyncio

from openai import AsyncOpenAI
from anthropic import AsyncAnthropic

from app.config import settings
from app.models.schemas import (
    AIClassificationResult,
    Classification,
    Document,
)

CLASSIFICATION_PROMPT = """You are an expert classifier for patents and research papers.
Analyze the following document and classify it into a technical category.

Title: {title}
Abstract: {abstract}
Document Type: {doc_type}

Respond ONLY with valid JSON in this exact format:
{{
    "category": "main technical category (e.g., Machine Learning, Biotechnology, Renewable Energy, etc.)",
    "subcategory": "more specific subcategory or null",
    "confidence": 0.0 to 1.0,
    "keywords": ["keyword1", "keyword2", "keyword3"],
    "reasoning": "brief explanation of why this classification was chosen"
}}
"""


def _parse_classification_response(raw: str, model_name: str) -> AIClassificationResult:
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

    data = json.loads(text)

    classification = Classification(
        category=data["category"],
        subcategory=data.get("subcategory"),
        confidence=float(data["confidence"]),
        keywords=data.get("keywords", []),
    )

    return AIClassificationResult(
        model_name=model_name,
        classification=classification,
        reasoning=data.get("reasoning", ""),
    )


async def classify_with_gpt(document: Document) -> AIClassificationResult:
    client = AsyncOpenAI(api_key=settings.openai_api_key)

    prompt = CLASSIFICATION_PROMPT.format(
        title=document.title,
        abstract=document.abstract,
        doc_type=document.doc_type.value,
    )

    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
    )

    raw = response.choices[0].message.content
    return _parse_classification_response(raw, "gpt-4o")


async def classify_with_claude(document: Document) -> AIClassificationResult:
    client = AsyncAnthropic(api_key=settings.anthropic_api_key)

    prompt = CLASSIFICATION_PROMPT.format(
        title=document.title,
        abstract=document.abstract,
        doc_type=document.doc_type.value,
    )

    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
    )

    raw = response.content[0].text
    return _parse_classification_response(raw, "claude-sonnet-4-20250514")


async def classify_document(document: Document) -> Document:
    gpt_result, claude_result = await asyncio.gather(
        classify_with_gpt(document),
        classify_with_claude(document),
    )

    document.gpt_classification = gpt_result
    document.claude_classification = claude_result

    return document
