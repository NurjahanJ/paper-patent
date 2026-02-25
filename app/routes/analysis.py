from fastapi import APIRouter

from app.services.gap_analysis import (
    gap_summary,
    gap_by_five_year_periods,
    patent_class_frequency_by_year,
    paper_class_frequency_by_year,
)
from app.services.linking import link_patents_to_papers, crossref_assignees

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.get("/gaps")
async def get_gap_analysis():
    """Goal 3: Gap analysis — which classes have patents vs papers."""
    return gap_summary()


@router.get("/gaps/by-year")
async def get_gap_by_year():
    """Patent and paper class frequency by year."""
    return {
        "patent_frequency": patent_class_frequency_by_year(),
        "paper_frequency": paper_class_frequency_by_year(),
    }


@router.get("/gaps/five-year")
async def get_gap_five_year():
    """Gap analysis by 5-year periods (as shown in assignment example)."""
    return gap_by_five_year_periods()


@router.post("/link-patents")
async def run_patent_paper_linking(top_n: int = 3):
    """Goal 3 (part 2): Link each patent to its top N most related papers."""
    return link_patents_to_papers(top_n=top_n)


@router.post("/crossref-assignees")
async def run_assignee_crossref():
    """Goal 4: Find patent assignees who also published papers on the same topic."""
    return crossref_assignees()
