from fastapi import APIRouter
from fastapi.responses import FileResponse

from app.services.export import (
    export_classified_papers,
    export_classified_patents,
    export_gap_analysis,
    export_patent_paper_links,
    export_assignee_crossrefs,
)

router = APIRouter(prefix="/export", tags=["export"])


@router.post("/papers")
async def export_papers():
    """Goal 1: Export classified papers as sorted CSV."""
    path = export_classified_papers()
    return FileResponse(path, media_type="text/csv", filename="classified_papers.csv")


@router.post("/patents")
async def export_patents():
    """Goal 2: Export classified patents as sorted CSV."""
    path = export_classified_patents()
    return FileResponse(path, media_type="text/csv", filename="classified_patents.csv")


@router.post("/gaps")
async def export_gaps():
    """Export gap analysis as CSV."""
    path = export_gap_analysis()
    return FileResponse(path, media_type="text/csv", filename="gap_analysis.csv")


@router.post("/links")
async def export_links():
    """Export patent-paper links as CSV."""
    path = export_patent_paper_links()
    return FileResponse(path, media_type="text/csv", filename="patent_paper_links.csv")


@router.post("/crossrefs")
async def export_crossrefs():
    """Export assignee cross-references as CSV."""
    path = export_assignee_crossrefs()
    return FileResponse(path, media_type="text/csv", filename="assignee_crossrefs.csv")


@router.post("/all")
async def export_all():
    """Export everything at once."""
    papers_path = export_classified_papers()
    patents_path = export_classified_patents()
    gaps_path = export_gap_analysis()
    links_path = export_patent_paper_links()
    crossrefs_path = export_assignee_crossrefs()

    return {
        "files": [papers_path, patents_path, gaps_path, links_path, crossrefs_path],
        "message": "All exports generated in the output/ directory.",
    }
