from fastapi import APIRouter, HTTPException

from app.models.schemas import (
    ClassificationStatus,
    ClassifyRequest,
    Document,
    DocumentCreate,
)
from app.services.classifier import classify_document
from app.services.consensus import check_consensus
from app.services.storage import (
    add_document,
    get_document_by_id,
    load_documents,
    update_document,
    delete_document,
)

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("/", response_model=list[Document])
async def list_documents():
    return load_documents()


@router.get("/{doc_id}", response_model=Document)
async def get_document(doc_id: str):
    doc = get_document_by_id(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.post("/", response_model=Document)
async def create_document(data: DocumentCreate):
    doc = Document(**data.model_dump())
    return add_document(doc)


@router.delete("/{doc_id}")
async def remove_document(doc_id: str):
    if not delete_document(doc_id):
        raise HTTPException(status_code=404, detail="Document not found")
    return {"detail": "Document deleted"}


@router.post("/classify", response_model=list[Document])
async def classify_documents(request: ClassifyRequest):
    documents = load_documents()

    if request.document_ids:
        targets = [d for d in documents if d.id in request.document_ids]
        if not targets:
            raise HTTPException(status_code=404, detail="No matching documents found")
    else:
        targets = [d for d in documents if d.status == ClassificationStatus.PENDING]
        if not targets:
            raise HTTPException(status_code=400, detail="No pending documents to classify")

    results = []
    for doc in targets:
        try:
            classified = await classify_document(doc)
            classified = check_consensus(classified)
            update_document(classified)
            results.append(classified)
        except Exception as e:
            doc.status = ClassificationStatus.PENDING
            update_document(doc)
            raise HTTPException(
                status_code=500,
                detail=f"Classification failed for '{doc.title}': {str(e)}",
            )

    return results
