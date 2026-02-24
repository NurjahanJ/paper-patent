from fastapi import APIRouter, HTTPException

from app.models.schemas import (
    ClassificationStatus,
    Document,
    HumanReviewRequest,
)
from app.services.storage import get_document_by_id, load_documents, update_document

router = APIRouter(prefix="/review", tags=["review"])


@router.get("/pending", response_model=list[Document])
async def list_disagreements():
    documents = load_documents()
    return [d for d in documents if d.status == ClassificationStatus.DISAGREED]


@router.post("/resolve", response_model=Document)
async def resolve_disagreement(request: HumanReviewRequest):
    doc = get_document_by_id(request.document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if doc.status != ClassificationStatus.DISAGREED:
        raise HTTPException(
            status_code=400,
            detail=f"Document status is '{doc.status.value}', not 'disagreed'. Only disagreed documents can be reviewed.",
        )

    doc.final_classification = request.chosen_classification
    doc.human_review_note = request.note
    doc.status = ClassificationStatus.HUMAN_REVIEWED
    update_document(doc)

    return doc
