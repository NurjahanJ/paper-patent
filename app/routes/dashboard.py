"""Dashboard route: serves the main project dashboard and its data APIs."""
import shutil
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, FileResponse

from app import db
from app.config import settings
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


@router.get("/dashboard/api/results")
async def dashboard_results():
    """Comprehensive results data for the Results page."""
    counts = db.count_documents()
    with transaction() as conn:
        agreed = conn.execute("SELECT COUNT(*) FROM classifications WHERE status = 'agreed'").fetchone()[0]
        disagreed = conn.execute("SELECT COUNT(*) FROM classifications WHERE status = 'disagreed'").fetchone()[0]
        human_reviewed = conn.execute("SELECT COUNT(*) FROM classifications WHERE status = 'human_reviewed'").fetchone()[0]

        # Top primary classes for papers
        top_paper_classes = conn.execute(
            """SELECT c.final_primary AS code, COUNT(*) AS cnt
               FROM classifications c JOIN documents d ON c.serial_number = d.serial_number
               WHERE d.doc_type = 'paper' AND c.status IN ('agreed','human_reviewed')
               GROUP BY c.final_primary ORDER BY cnt DESC LIMIT 10"""
        ).fetchall()

        # Top primary classes for patents
        top_patent_classes = conn.execute(
            """SELECT c.final_primary AS code, COUNT(*) AS cnt
               FROM classifications c JOIN documents d ON c.serial_number = d.serial_number
               WHERE d.doc_type = 'patent' AND c.status IN ('agreed','human_reviewed')
               GROUP BY c.final_primary ORDER BY cnt DESC LIMIT 10"""
        ).fetchall()

        # Disagreement analysis: most common GPT vs Claude disagreement pairs
        disagreement_pairs = conn.execute(
            """SELECT gpt.primary_code AS gpt_code, claude.primary_code AS claude_code, COUNT(*) AS cnt
               FROM classifications c
               JOIN ai_results gpt ON c.serial_number = gpt.serial_number AND gpt.model_name = 'gpt'
               JOIN ai_results claude ON c.serial_number = claude.serial_number AND claude.model_name = 'claude'
               WHERE c.status IN ('disagreed','human_reviewed')
               GROUP BY gpt.primary_code, claude.primary_code
               ORDER BY cnt DESC LIMIT 15"""
        ).fetchall()

        # For human-reviewed: how often did the human pick GPT vs Claude vs something else
        human_picked_gpt = conn.execute(
            """SELECT COUNT(*) FROM classifications c
               JOIN ai_results gpt ON c.serial_number = gpt.serial_number AND gpt.model_name = 'gpt'
               WHERE c.status = 'human_reviewed' AND c.final_primary = gpt.primary_code"""
        ).fetchone()[0]
        human_picked_claude = conn.execute(
            """SELECT COUNT(*) FROM classifications c
               JOIN ai_results claude ON c.serial_number = claude.serial_number AND claude.model_name = 'claude'
               WHERE c.status = 'human_reviewed' AND c.final_primary = claude.primary_code"""
        ).fetchone()[0]

        # Year range
        year_range = conn.execute(
            "SELECT MIN(year), MAX(year) FROM documents WHERE year IS NOT NULL AND year > 0"
        ).fetchone()

        # Papers by decade
        papers_by_decade = conn.execute(
            """SELECT (d.year / 10) * 10 AS decade, COUNT(*) AS cnt
               FROM documents d JOIN classifications c ON d.serial_number = c.serial_number
               WHERE d.doc_type = 'paper' AND d.year > 0 AND c.status IN ('agreed','human_reviewed')
               GROUP BY decade ORDER BY decade"""
        ).fetchall()

        # Patents by decade
        patents_by_decade = conn.execute(
            """SELECT (d.year / 10) * 10 AS decade, COUNT(*) AS cnt
               FROM documents d JOIN classifications c ON d.serial_number = c.serial_number
               WHERE d.doc_type = 'patent' AND d.year > 0 AND c.status IN ('agreed','human_reviewed')
               GROUP BY decade ORDER BY decade"""
        ).fetchall()

        # Link stats
        total_links = conn.execute("SELECT COUNT(*) FROM paper_patent_links").fetchone()[0]
        avg_similarity = conn.execute("SELECT AVG(similarity_score) FROM paper_patent_links").fetchone()[0]
        max_similarity = conn.execute("SELECT MAX(similarity_score) FROM paper_patent_links").fetchone()[0]

        # Crossref count
        total_crossrefs = conn.execute("SELECT COUNT(*) FROM assignee_crossrefs").fetchone()[0]

    # Gap summary
    gaps = gap_summary()
    papers_only_classes = [c for c in gaps["by_class"] if c["gap_type"] == "papers_only"]
    both_classes = [c for c in gaps["by_class"] if c["gap_type"] == "both"]
    empty_classes = [c for c in gaps["by_class"] if c["gap_type"] == "empty"]

    return {
        "counts": counts,
        "agreed": agreed,
        "disagreed": disagreed,
        "human_reviewed": human_reviewed,
        "agreement_rate": round(agreed / (agreed + disagreed + human_reviewed) * 100, 1) if (agreed + disagreed + human_reviewed) > 0 else 0,
        "top_paper_classes": [dict(r) for r in top_paper_classes],
        "top_patent_classes": [dict(r) for r in top_patent_classes],
        "disagreement_pairs": [dict(r) for r in disagreement_pairs],
        "human_picked_gpt": human_picked_gpt,
        "human_picked_claude": human_picked_claude,
        "human_picked_other": human_reviewed - human_picked_gpt - human_picked_claude,
        "year_range": {"min": year_range[0], "max": year_range[1]} if year_range else None,
        "papers_by_decade": [dict(r) for r in papers_by_decade],
        "patents_by_decade": [dict(r) for r in patents_by_decade],
        "total_links": total_links,
        "avg_similarity": round(avg_similarity * 100, 1) if avg_similarity else 0,
        "max_similarity": round(max_similarity * 100, 1) if max_similarity else 0,
        "total_crossrefs": total_crossrefs,
        "papers_only_classes": papers_only_classes,
        "both_classes": both_classes,
        "empty_classes": empty_classes,
        "classes_with_no_patents": gaps["classes_with_no_patents"],
    }


@router.get("/dashboard/api/taxonomy")
async def dashboard_taxonomy():
    """Taxonomy lookup for the frontend."""
    return {str(k): {"code": v.code, "category": v.major_category, "description": v.description}
            for k, v in TAXONOMY.items()}


@router.get("/dashboard/api/download-db")
async def download_database():
    """Download the current database file for backup or local sync."""
    db_path = Path(settings.db_path)
    if not db_path.exists():
        raise HTTPException(status_code=404, detail="Database file not found")
    return FileResponse(
        path=str(db_path),
        filename="ferrofluids.db",
        media_type="application/octet-stream",
    )


@router.post("/dashboard/api/upload-db")
async def upload_database(file: UploadFile = File(...)):
    """Upload a database file to replace the current one.
    
    Use this to restore a backup or sync your local database to Render.
    The uploaded file must be named ferrofluids.db.
    """
    db_path = Path(settings.db_path)
    backup_path = db_path.with_suffix(".db.bak")
    
    # Create a backup of the current database
    if db_path.exists():
        shutil.copy2(db_path, backup_path)
    
    try:
        # Write the uploaded file
        with open(db_path, "wb") as f:
            content = await file.read()
            f.write(content)
        return {
            "status": "success",
            "message": f"Database uploaded ({len(content):,} bytes)",
            "backup": str(backup_path),
        }
    except Exception:
        # Restore backup on failure
        if backup_path.exists():
            shutil.copy2(backup_path, db_path)
        raise


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page():
    """Main dashboard page."""
    return HTMLResponse((_TEMPLATE_DIR / "dashboard.html").read_text(encoding="utf-8"))
