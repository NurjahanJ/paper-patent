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
    """Return review progress stats."""
    with transaction() as conn:
        agreed = conn.execute("SELECT COUNT(1) FROM classifications WHERE status='agreed'").fetchone()[0]
        disagreed = conn.execute("SELECT COUNT(1) FROM classifications WHERE status='disagreed'").fetchone()[0]
        reviewed = conn.execute("SELECT COUNT(1) FROM classifications WHERE status='human_reviewed'").fetchone()[0]
    return {"agreed": agreed, "disagreed": disagreed, "human_reviewed": reviewed}


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


# Standalone review UI removed - review functionality is now integrated into the main dashboard
# at /dashboard (see "Review Disagreements" tab)
# The API endpoints above (/review/ui/taxonomy, /review/ui/stats, /review/ui/next) are still used by the dashboard
