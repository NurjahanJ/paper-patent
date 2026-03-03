from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from app import db
from app.db.connection import transaction

router = APIRouter(tags=["progress"])

_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"


@router.get("/progress/api")
async def progress_api():
    """JSON endpoint for live progress data."""
    counts = db.count_documents()

    with transaction() as conn:
        agreed = conn.execute(
            "SELECT COUNT(*) FROM classifications WHERE status = 'agreed'"
        ).fetchone()[0]
        disagreed = conn.execute(
            "SELECT COUNT(*) FROM classifications WHERE status = 'disagreed'"
        ).fetchone()[0]
        human_reviewed = conn.execute(
            "SELECT COUNT(*) FROM classifications WHERE status = 'human_reviewed'"
        ).fetchone()[0]

    classified = counts["classified"]
    total = counts["total"]
    pct = round(100 * classified / total, 1) if total > 0 else 0

    return {
        "total": total,
        "papers": counts["papers"],
        "patents": counts["patents"],
        "classified": classified,
        "pending": counts["pending"],
        "agreed": agreed,
        "disagreed": disagreed,
        "human_reviewed": human_reviewed,
        "percent": pct,
    }


@router.get("/progress", response_class=HTMLResponse)
async def progress_dashboard():
    """Live progress dashboard."""
    return HTMLResponse((_TEMPLATE_DIR / "progress.html").read_text(encoding="utf-8"))
