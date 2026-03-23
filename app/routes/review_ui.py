from fastapi import APIRouter

from app import db
from app.db.connection import transaction
from app.taxonomy import TAXONOMY

router = APIRouter(tags=["review-ui"])


@router.get("/review/ui/taxonomy")
async def taxonomy_json():
    """Return taxonomy as JSON for the UI."""
    return {str(k): {"code": v.code, "category": v.major_category, "description": v.description}
            for k, v in TAXONOMY.items()}


@router.get("/review/ui/stats")
async def review_stats():
    """Return review progress stats and AI accuracy tracking."""
    with transaction() as conn:
        agreed = conn.execute("SELECT COUNT(1) FROM classifications WHERE status='agreed'").fetchone()[0]
        disagreed = conn.execute("SELECT COUNT(1) FROM classifications WHERE status='disagreed'").fetchone()[0]
        reviewed = conn.execute("SELECT COUNT(1) FROM classifications WHERE status='human_reviewed'").fetchone()[0]
        
        # AI accuracy tracking
        gpt_correct = conn.execute("SELECT COUNT(1) FROM classifications WHERE correct_model='gpt-4o'").fetchone()[0]
        claude_correct = conn.execute("SELECT COUNT(1) FROM classifications WHERE correct_model='claude-sonnet'").fetchone()[0]
        neither_correct = conn.execute("SELECT COUNT(1) FROM classifications WHERE status='human_reviewed' AND correct_model IS NULL").fetchone()[0]
        
    total_reviewed = gpt_correct + claude_correct + neither_correct
    return {
        "agreed": agreed, 
        "disagreed": disagreed, 
        "human_reviewed": reviewed,
        "accuracy": {
            "gpt_correct": gpt_correct,
            "claude_correct": claude_correct,
            "neither_correct": neither_correct,
            "total_reviewed": total_reviewed,
            "gpt_accuracy": round(gpt_correct / total_reviewed * 100, 1) if total_reviewed > 0 else 0,
            "claude_accuracy": round(claude_correct / total_reviewed * 100, 1) if total_reviewed > 0 else 0
        }
    }


@router.get("/review/ui/next")
async def next_disagreement(offset: int = 0):
    """Get the next unreviewed disagreement."""
    with transaction() as conn:
        row = conn.execute(
            "SELECT serial_number FROM classifications WHERE status='disagreed' LIMIT 1 OFFSET ?",
            (offset,)
        ).fetchone()
    if not row:
        return {"done": True}
    serial = row["serial_number"]
    doc = db.get_document(serial)
    classification = db.get_classification(serial)
    remaining = db.get_classifications_by_status("disagreed")
    return {"done": False, "document": doc, "classification": classification, "remaining": len(remaining)}


@router.get("/review/ui/reviewed")
async def list_human_reviewed():
    """Return all human-reviewed documents with which AI was correct."""
    with transaction() as conn:
        rows = conn.execute(
            """SELECT c.serial_number, c.final_primary, c.correct_model, c.final_reasoning,
                      d.doc_type, d.title, d.year,
                      gpt.primary_code AS gpt_primary,
                      claude.primary_code AS claude_primary
               FROM classifications c
               JOIN documents d ON c.serial_number = d.serial_number
               LEFT JOIN ai_results gpt ON c.serial_number = gpt.serial_number AND gpt.model_name = 'gpt'
               LEFT JOIN ai_results claude ON c.serial_number = claude.serial_number AND claude.model_name = 'claude'
               WHERE c.status = 'human_reviewed'
               ORDER BY c.serial_number"""
        ).fetchall()
    return {"count": len(rows), "items": [dict(r) for r in rows]}
