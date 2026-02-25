from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app import db
from app.taxonomy import VALID_CODES

router = APIRouter(prefix="/review", tags=["review"])


class ReviewRequest(BaseModel):
    serial_number: str
    primary: int
    secondary: int
    tertiary: int
    note: Optional[str] = None


@router.get("/pending")
async def list_disagreements():
    """List all documents where GPT and Claude disagreed."""
    disagreed = db.get_classifications_by_status("disagreed")
    results = []
    for c in disagreed:
        doc = db.get_document(c["serial_number"])
        results.append({"document": doc, "classification": c})
    return {"count": len(results), "items": results}


@router.post("/resolve")
async def resolve_disagreement(request: ReviewRequest):
    """Human review: finalize classification for a disagreed document."""
    for code in [request.primary, request.secondary, request.tertiary]:
        if code not in VALID_CODES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid class code {code}. Valid: {sorted(VALID_CODES)}"
            )

    existing = db.get_classification(request.serial_number)
    if not existing:
        raise HTTPException(status_code=404, detail="Classification not found")
    if existing["status"] not in ("disagreed", "pending"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot review: status is '{existing['status']}', expected 'disagreed' or 'pending'"
        )

    note = request.note or "Human reviewed"
    db.finalize_classification(
        request.serial_number,
        request.primary,
        request.secondary,
        request.tertiary,
        note,
        "human_reviewed",
    )

    return {"status": "resolved", "serial_number": request.serial_number}
