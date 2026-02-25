import json
import logging
import os
from pathlib import Path

import pandas as pd

from app.db.connection import transaction
from app.services.gap_analysis import gap_summary, gap_by_five_year_periods
from app.taxonomy import get_class_description

logger = logging.getLogger(__name__)

OUTPUT_DIR = "output"


def _ensure_output_dir():
    Path(OUTPUT_DIR).mkdir(exist_ok=True)


def _fetch_classified_rows(doc_type: str) -> list:
    """Shared query for fetching classified documents by type."""
    with transaction() as conn:
        rows = conn.execute(
            """SELECT d.serial_number, d.year, d.title, d.original_data,
                      c.final_primary, c.final_secondary, c.final_tertiary,
                      c.final_reasoning, c.status,
                      gpt.primary_code AS gpt_primary, claude.primary_code AS claude_primary
               FROM documents d
               JOIN classifications c ON d.serial_number = c.serial_number
               LEFT JOIN ai_results gpt ON d.serial_number = gpt.serial_number AND gpt.model_name = 'gpt'
               LEFT JOIN ai_results claude ON d.serial_number = claude.serial_number AND claude.model_name = 'claude'
               WHERE d.doc_type = ? AND c.status IN ('agreed', 'human_reviewed')
               ORDER BY d.year, c.final_primary, c.final_secondary, c.final_tertiary""",
            (doc_type,)
        ).fetchall()
    return rows


def export_classified_papers(filepath: str = None) -> str:
    """
    Goal 1: Export classified papers as CSV sorted by Year, Primary, Secondary, Tertiary.
    Preserves all original columns + adds classification columns.
    """
    _ensure_output_dir()
    if filepath is None:
        filepath = os.path.join(OUTPUT_DIR, "classified_papers.csv")

    rows = _fetch_classified_rows("paper")
    return _export_rows(rows, filepath, "papers")


def export_classified_patents(filepath: str = None) -> str:
    """Goal 2: Export classified patents as CSV, same format."""
    _ensure_output_dir()
    if filepath is None:
        filepath = os.path.join(OUTPUT_DIR, "classified_patents.csv")

    rows = _fetch_classified_rows("patent")
    return _export_rows(rows, filepath, "patents")


def _export_rows(rows: list, filepath: str, label: str) -> str:
    records = []
    for row in rows:
        row = dict(row)
        original = json.loads(row["original_data"])

        record = {
            "Serial Number": row["serial_number"],
            "Year": row["year"],
            "Title": row["title"],
            "Primary Class": row["final_primary"],
            "Primary Desc": get_class_description(row["final_primary"]) if row["final_primary"] else "",
            "Secondary Class": row["final_secondary"],
            "Secondary Desc": get_class_description(row["final_secondary"]) if row["final_secondary"] else "",
            "Tertiary Class": row["final_tertiary"],
            "Tertiary Desc": get_class_description(row["final_tertiary"]) if row["final_tertiary"] else "",
            "Reasoning": row["final_reasoning"],
            "GPT Primary": row["gpt_primary"],
            "Claude Primary": row["claude_primary"],
            "Consensus Status": row["status"],
        }

        # Append all original columns
        for col, val in original.items():
            if col not in ("Title", "Year", "#"):
                record[f"Original_{col}"] = val

        records.append(record)

    df = pd.DataFrame(records)
    df.to_csv(filepath, index=False, encoding="utf-8-sig")
    logger.info("Exported %d %s to %s", len(records), label, filepath)
    return filepath


def export_gap_analysis(filepath: str = None) -> str:
    """Export gap analysis as CSV."""
    _ensure_output_dir()
    if filepath is None:
        filepath = os.path.join(OUTPUT_DIR, "gap_analysis.csv")

    summary = gap_summary()
    df = pd.DataFrame(summary["by_class"])
    df.to_csv(filepath, index=False, encoding="utf-8-sig")

    # Also export 5-year period breakdown
    periods_path = os.path.join(OUTPUT_DIR, "gap_by_5year_periods.csv")
    periods = gap_by_five_year_periods()
    if periods:
        pd.DataFrame(periods).to_csv(periods_path, index=False, encoding="utf-8-sig")
        logger.info("Exported 5-year gap analysis to %s", periods_path)

    logger.info("Exported gap analysis to %s", filepath)
    return filepath


def export_patent_paper_links(filepath: str = None) -> str:
    """Export patent-to-paper links as CSV."""
    _ensure_output_dir()
    if filepath is None:
        filepath = os.path.join(OUTPUT_DIR, "patent_paper_links.csv")

    with transaction() as conn:
        rows = conn.execute(
            """SELECT l.patent_serial, l.paper_serial, l.similarity_score,
                      dp.title AS patent_title, dp.year AS patent_year,
                      dr.title AS paper_title, dr.year AS paper_year
               FROM paper_patent_links l
               JOIN documents dp ON l.patent_serial = dp.serial_number
               JOIN documents dr ON l.paper_serial = dr.serial_number
               ORDER BY l.patent_serial, l.similarity_score DESC"""
        ).fetchall()

    df = pd.DataFrame([dict(r) for r in rows])
    df.to_csv(filepath, index=False, encoding="utf-8-sig")
    logger.info("Exported %d patent-paper links to %s", len(df), filepath)
    return filepath


def export_assignee_crossrefs(filepath: str = None) -> str:
    """Export assignee cross-references as CSV."""
    _ensure_output_dir()
    if filepath is None:
        filepath = os.path.join(OUTPUT_DIR, "assignee_crossrefs.csv")

    with transaction() as conn:
        rows = conn.execute(
            """SELECT a.patent_serial, a.paper_serial, a.matched_name,
                      dp.title AS patent_title, dp.year AS patent_year,
                      dr.title AS paper_title, dr.year AS paper_year
               FROM assignee_crossrefs a
               JOIN documents dp ON a.patent_serial = dp.serial_number
               JOIN documents dr ON a.paper_serial = dr.serial_number
               ORDER BY a.matched_name, dp.year"""
        ).fetchall()

    df = pd.DataFrame([dict(r) for r in rows])
    df.to_csv(filepath, index=False, encoding="utf-8-sig")
    logger.info("Exported %d assignee cross-refs to %s", len(df), filepath)
    return filepath
