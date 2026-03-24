from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app import db
from app.db.connection import transaction
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
    with transaction() as conn:
        rows = conn.execute(
            """SELECT d.serial_number, d.doc_type, d.title, d.abstract, d.year,
                      d.authors, d.source,
                      c.final_primary, c.final_secondary, c.final_tertiary,
                      c.final_reasoning, c.status,
                      gpt.primary_code AS gpt_primary, gpt.reasoning AS gpt_reasoning,
                      claude.primary_code AS claude_primary, claude.reasoning AS claude_reasoning
               FROM classifications c
               JOIN documents d ON c.serial_number = d.serial_number
               LEFT JOIN ai_results gpt ON c.serial_number = gpt.serial_number AND gpt.model_name = 'gpt'
               LEFT JOIN ai_results claude ON c.serial_number = claude.serial_number AND claude.model_name = 'claude'
               WHERE c.status = 'disagreed'
               ORDER BY d.year, d.serial_number"""
        ).fetchall()

    items = []
    for r in rows:
        r = dict(r)
        doc = {k: r[k] for k in ("serial_number", "doc_type", "title", "abstract", "year", "authors", "source")}
        classification = {k: r[k] for k in ("serial_number", "final_primary", "final_secondary",
                          "final_tertiary", "final_reasoning", "status",
                          "gpt_primary", "gpt_reasoning", "claude_primary", "claude_reasoning")}
        items.append({"document": doc, "classification": classification})

    return {"count": len(items), "items": items}


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

    # Determine which AI model was correct based on human's primary code choice
    correct_model = None
    if existing["status"] == "disagreed":
        gpt_primary = existing.get("gpt_primary")
        claude_primary = existing.get("claude_primary")
        if request.primary == gpt_primary:
            correct_model = "gpt-4o"
        elif request.primary == claude_primary:
            correct_model = "claude-sonnet"
        # If neither matches, correct_model stays None (human chose different classification)

    note = request.note or "Human reviewed"
    db.finalize_classification(
        request.serial_number,
        request.primary,
        request.secondary,
        request.tertiary,
        note,
        "human_reviewed",
        correct_model,
    )

    return {"status": "resolved", "serial_number": request.serial_number, "correct_model": correct_model}
