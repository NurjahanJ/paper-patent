import logging
from typing import Optional

import pandas as pd

from app import db

logger = logging.getLogger(__name__)


def _clean_str(val) -> Optional[str]:
    if pd.isna(val):
        return None
    s = str(val).strip()
    return s if s and s.lower() != "nan" else None


def _clean_int(val) -> Optional[int]:
    if pd.isna(val):
        return None
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return None


def import_papers(csv_path: str) -> dict:
    df = pd.read_csv(csv_path)
    logger.info("Loading papers from %s (%d rows)", csv_path, len(df))

    imported = 0
    skipped = 0
    seen_titles = set()

    for _, row in df.iterrows():
        title = _clean_str(row.get("Title"))
        abstract = _clean_str(row.get("Abstract"))

        if not title or not abstract:
            skipped += 1
            continue

        # Deduplicate by normalized title
        norm_title = title.strip().lower()
        if norm_title in seen_titles:
            skipped += 1
            continue
        seen_titles.add(norm_title)

        # Serial number: use the '#' column, prefix with P for papers
        raw_serial = row.get("#")
        serial = f"P{raw_serial}" if pd.notna(raw_serial) else f"P_auto_{imported}"

        authors_raw = _clean_str(row.get("Authors"))
        authors = [a.strip() for a in authors_raw.split(",") if a.strip()] if authors_raw else []

        year = _clean_int(row.get("Year"))
        source = _clean_str(row.get("Source title"))

        # Preserve full original row
        original_data = {col: (None if pd.isna(row[col]) else row[col]) for col in df.columns}

        db.insert_document(
            serial_number=serial,
            doc_type="paper",
            title=title,
            abstract=abstract,
            year=year,
            authors=authors,
            source=source,
            original_data=original_data,
        )
        imported += 1

    summary = {"imported": imported, "skipped": skipped, "source": csv_path}
    logger.info("Papers import: %s", summary)
    return summary


def import_patents(csv_path: str) -> dict:
    df = pd.read_csv(csv_path)
    logger.info("Loading patents from %s (%d rows)", csv_path, len(df))

    imported = 0
    skipped = 0
    seen_titles = set()

    for _, row in df.iterrows():
        title = _clean_str(row.get("Title"))
        abstract = _clean_str(row.get("Abstract"))

        if not title or not abstract:
            skipped += 1
            continue

        norm_title = title.strip().lower()
        if norm_title in seen_titles:
            skipped += 1
            continue
        seen_titles.add(norm_title)

        # Serial number: use '#' column, prefix with PT for patents
        raw_serial = row.get("#")
        serial = f"PT{raw_serial}" if pd.notna(raw_serial) else f"PT_auto_{imported}"

        inventors_raw = _clean_str(row.get("Inventors"))
        authors = [a.strip() for a in inventors_raw.split(";") if a.strip()] if inventors_raw else []

        year = _clean_int(row.get("Publication Year"))
        source = _clean_str(row.get("Display Key"))

        original_data = {col: (None if pd.isna(row[col]) else row[col]) for col in df.columns}

        db.insert_document(
            serial_number=serial,
            doc_type="patent",
            title=title,
            abstract=abstract,
            year=year,
            authors=authors,
            source=source,
            original_data=original_data,
        )
        imported += 1

    summary = {"imported": imported, "skipped": skipped, "source": csv_path}
    logger.info("Patents import: %s", summary)
    return summary


def import_all() -> dict:
    db.init_db()

    papers = import_papers("data/MANI_KW_PAPERS_scopus.csv")
    patents_a = import_patents("data/MANI_KW_PATENTS_A_weds1969to2009.csv")
    patents_b = import_patents("data/MANI_KW_PATENTS_B_weds2010tonow.csv")

    counts = db.count_documents()

    return {
        "papers": papers,
        "patents_a": patents_a,
        "patents_b": patents_b,
        "totals": counts,
    }
