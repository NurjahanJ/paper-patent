from typing import Optional

from fastapi import APIRouter, HTTPException

from app import db
from app.services.importer import import_all

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/import")
async def import_data():
    """Load all CSV data into the database."""
    result = import_all()
    return result


@router.get("/stats")
async def get_stats():
    """Get document counts."""
    return db.count_documents()


@router.get("/")
async def list_documents(doc_type: Optional[str] = None, limit: int = 100, offset: int = 0):
    """List documents with optional type filter."""
    docs, total = db.get_documents_paginated(doc_type, limit=limit, offset=offset)
    return {
        "total": total,
        "showing": len(docs),
        "documents": docs,
    }


@router.get("/{serial_number}")
async def get_document(serial_number: str):
    """Get a single document by serial number."""
    doc = db.get_document(serial_number)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    classification = db.get_classification(serial_number)
    return {"document": doc, "classification": classification}
