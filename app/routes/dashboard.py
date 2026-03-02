"""Dashboard route: serves the main project dashboard and its data APIs."""
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from app import db
from app.db.connection import transaction
from app.taxonomy import TAXONOMY
from app.services.gap_analysis import gap_summary, gap_by_five_year_periods

router = APIRouter(tags=["dashboard"])

_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"


@router.get("/dashboard/api/overview")
async def dashboard_overview():
    """Aggregate stats for the overview cards."""
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
    return {
        **counts,
        "agreed": agreed,
        "disagreed": disagreed,
        "human_reviewed": human_reviewed,
    }


@router.get("/dashboard/api/gap-analysis")
async def dashboard_gap_analysis():
    """Gap analysis data for charts."""
    gaps = gap_summary()
    periods = gap_by_five_year_periods()
    return {"summary": gaps, "periods": periods}


@router.get("/dashboard/api/classified")
async def dashboard_classified(doc_type: str = "paper", limit: int = 100, offset: int = 0):
    """Paginated classified documents for tables."""
    with transaction() as conn:
        total = conn.execute(
            """SELECT COUNT(*) FROM documents d
               JOIN classifications c ON d.serial_number = c.serial_number
               WHERE d.doc_type = ? AND c.status IN ('agreed','human_reviewed')""",
            (doc_type,)
        ).fetchone()[0]
        rows = conn.execute(
            """SELECT d.serial_number, d.title, d.year, d.authors,
                      c.final_primary, c.final_secondary, c.final_tertiary,
                      c.status,
                      gpt.primary_code AS gpt_primary,
                      claude.primary_code AS claude_primary
               FROM documents d
               JOIN classifications c ON d.serial_number = c.serial_number
               LEFT JOIN ai_results gpt ON d.serial_number = gpt.serial_number AND gpt.model_name = 'gpt'
               LEFT JOIN ai_results claude ON d.serial_number = claude.serial_number AND claude.model_name = 'claude'
               WHERE d.doc_type = ? AND c.status IN ('agreed','human_reviewed')
               ORDER BY d.year, c.final_primary, c.final_secondary, c.final_tertiary
               LIMIT ? OFFSET ?""",
            (doc_type, limit, offset)
        ).fetchall()
    return {"total": total, "rows": [dict(r) for r in rows]}


@router.get("/dashboard/api/links")
async def dashboard_links(limit: int = 100, offset: int = 0):
    """Patent-paper links for table."""
    with transaction() as conn:
        total = conn.execute("SELECT COUNT(*) FROM paper_patent_links").fetchone()[0]
        rows = conn.execute(
            """SELECT l.patent_serial, l.paper_serial,
                      ROUND(l.similarity_score, 4) AS score,
                      dp.title AS patent_title, dp.year AS patent_year,
                      dr.title AS paper_title, dr.year AS paper_year
               FROM paper_patent_links l
               JOIN documents dp ON l.patent_serial = dp.serial_number
               JOIN documents dr ON l.paper_serial = dr.serial_number
               ORDER BY l.patent_serial, l.similarity_score DESC
               LIMIT ? OFFSET ?""",
            (limit, offset)
        ).fetchall()
    return {"total": total, "rows": [dict(r) for r in rows]}


@router.get("/dashboard/api/crossrefs")
async def dashboard_crossrefs():
    """Assignee cross-references."""
    with transaction() as conn:
        rows = conn.execute(
            """SELECT a.patent_serial, a.paper_serial, a.matched_name,
                      dp.title AS patent_title, dr.title AS paper_title
               FROM assignee_crossrefs a
               JOIN documents dp ON a.patent_serial = dp.serial_number
               JOIN documents dr ON a.paper_serial = dr.serial_number
               ORDER BY a.matched_name"""
        ).fetchall()
    return {"total": len(rows), "rows": [dict(r) for r in rows]}


@router.get("/dashboard/api/taxonomy")
async def dashboard_taxonomy():
    """Taxonomy lookup for the frontend."""
    return {str(k): {"code": v.code, "category": v.major_category, "description": v.description}
            for k, v in TAXONOMY.items()}


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page():
    """Main dashboard page."""
    return HTMLResponse((_TEMPLATE_DIR / "dashboard.html").read_text(encoding="utf-8"))
