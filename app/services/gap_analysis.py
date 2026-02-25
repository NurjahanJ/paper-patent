import logging
from collections import defaultdict

from app import db
from app.taxonomy import TAXONOMY, get_class_description

logger = logging.getLogger(__name__)


def patent_class_frequency_by_year() -> dict:
    """
    Goal 3: Which class has more patents, which has none, by year.
    Returns {year: {class_code: count}}.
    """
    conn = db.get_connection()
    try:
        rows = conn.execute(
            """SELECT d.year, c.final_primary, COUNT(*) as cnt
               FROM documents d
               JOIN classifications c ON d.serial_number = c.serial_number
               WHERE d.doc_type = 'patent' AND c.status IN ('agreed', 'human_reviewed')
               GROUP BY d.year, c.final_primary
               ORDER BY d.year, c.final_primary"""
        ).fetchall()
    finally:
        conn.close()

    result = defaultdict(lambda: defaultdict(int))
    for row in rows:
        if row["year"]:
            result[row["year"]][row["final_primary"]] = row["cnt"]

    return dict(result)


def paper_class_frequency_by_year() -> dict:
    """Same as above but for papers."""
    conn = db.get_connection()
    try:
        rows = conn.execute(
            """SELECT d.year, c.final_primary, COUNT(*) as cnt
               FROM documents d
               JOIN classifications c ON d.serial_number = c.serial_number
               WHERE d.doc_type = 'paper' AND c.status IN ('agreed', 'human_reviewed')
               GROUP BY d.year, c.final_primary
               ORDER BY d.year, c.final_primary"""
        ).fetchall()
    finally:
        conn.close()

    result = defaultdict(lambda: defaultdict(int))
    for row in rows:
        if row["year"]:
            result[row["year"]][row["final_primary"]] = row["cnt"]

    return dict(result)


def gap_summary() -> dict:
    """
    Consolidated gap analysis:
    - Which classes have patents vs papers
    - Which classes have NO patents
    - Totals per class per doc_type
    """
    conn = db.get_connection()
    try:
        rows = conn.execute(
            """SELECT d.doc_type, c.final_primary, COUNT(*) as cnt
               FROM documents d
               JOIN classifications c ON d.serial_number = c.serial_number
               WHERE c.status IN ('agreed', 'human_reviewed')
               GROUP BY d.doc_type, c.final_primary"""
        ).fetchall()
    finally:
        conn.close()

    paper_counts = {}
    patent_counts = {}
    for row in rows:
        code = row["final_primary"]
        if row["doc_type"] == "paper":
            paper_counts[code] = row["cnt"]
        else:
            patent_counts[code] = row["cnt"]

    gaps = []
    for code in sorted(TAXONOMY.keys()):
        papers = paper_counts.get(code, 0)
        patents = patent_counts.get(code, 0)
        gap_type = "none"
        if papers > 0 and patents == 0:
            gap_type = "papers_only"
        elif patents > 0 and papers == 0:
            gap_type = "patents_only"
        elif papers == 0 and patents == 0:
            gap_type = "empty"
        elif papers > 0 and patents > 0:
            gap_type = "both"

        gaps.append({
            "code": code,
            "description": get_class_description(code),
            "papers": papers,
            "patents": patents,
            "gap_type": gap_type,
        })

    return {
        "by_class": gaps,
        "total_papers_classified": sum(paper_counts.values()),
        "total_patents_classified": sum(patent_counts.values()),
        "classes_with_no_patents": [g["code"] for g in gaps if g["gap_type"] in ("papers_only", "empty")],
        "classes_with_no_papers": [g["code"] for g in gaps if g["gap_type"] in ("patents_only", "empty")],
    }


def gap_by_five_year_periods() -> list[dict]:
    """
    Gap analysis consolidated by 5-year periods as mentioned in the assignment.
    Returns list of {period, class_code, description, paper_count, patent_count}.
    """
    patent_freq = patent_class_frequency_by_year()
    paper_freq = paper_class_frequency_by_year()

    all_years = set()
    for year_dict in [patent_freq, paper_freq]:
        all_years.update(year_dict.keys())

    if not all_years:
        return []

    min_year = min(all_years)
    max_year = max(all_years)

    # Create 5-year buckets
    periods = []
    start = (min_year // 5) * 5
    while start <= max_year:
        end = start + 4
        period_label = f"{start}-{end}"

        for code in sorted(TAXONOMY.keys()):
            paper_total = 0
            patent_total = 0
            for y in range(start, end + 1):
                paper_total += paper_freq.get(y, {}).get(code, 0)
                patent_total += patent_freq.get(y, {}).get(code, 0)

            if paper_total > 0 or patent_total > 0:
                periods.append({
                    "period": period_label,
                    "code": code,
                    "description": get_class_description(code),
                    "papers": paper_total,
                    "patents": patent_total,
                })

        start += 5

    return periods
