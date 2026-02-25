import logging
from typing import Optional

from fastapi import APIRouter

from app.services.pipeline import run_classification

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/classify", tags=["classify"])


@router.post("/")
async def classify_documents(
    doc_type: Optional[str] = None,
    limit: Optional[int] = None,
    concurrency: Optional[int] = None,
):
    """
    Run the dual AI classification pipeline.
    - Resumes from where it left off.
    - doc_type: 'paper' or 'patent' (or None for all)
    - limit: max documents to classify in this run
    - concurrency: number of parallel requests
    """
    result = await run_classification(
        doc_type=doc_type,
        limit=limit,
        concurrency=concurrency,
    )
    return result
