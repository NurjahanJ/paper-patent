import logging
from dataclasses import dataclass
from typing import Optional

import pandas as pd

from app import db
from app.db.connection import transaction

logger = logging.getLogger(__name__)


@dataclass
class CsvMapping:
    """Column mapping config for importing a CSV."""
    doc_type: str
    serial_prefix: str
    authors_column: str
    authors_delimiter: str
    year_column: str
    source_column: str


PAPER_MAPPING = CsvMapping(
    doc_type="paper",
    serial_prefix="P",
    authors_column="Authors",
    authors_delimiter=",",
    year_column="Year",
    source_column="Source title",
)

PATENT_MAPPING = CsvMapping(
    doc_type="patent",
    serial_prefix="PT",
    authors_column="Inventors",
    authors_delimiter=";",
    year_column="Publication Year",
    source_column="Display Key",
)


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


def import_csv(csv_path: str, mapping: CsvMapping) -> dict:
    """Generic CSV import using a column mapping."""
    df = pd.read_csv(csv_path)
    logger.info("Loading %ss from %s (%d rows)", mapping.doc_type, csv_path, len(df))

    imported = 0
    skipped = 0
    seen_titles = set()

    with transaction() as conn:
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

            raw_serial = row.get("#")
            serial = (
                f"{mapping.serial_prefix}{raw_serial}"
                if pd.notna(raw_serial)
                else f"{mapping.serial_prefix}_auto_{imported}"
            )

            authors_raw = _clean_str(row.get(mapping.authors_column))
            authors = (
                [a.strip() for a in authors_raw.split(mapping.authors_delimiter) if a.strip()]
                if authors_raw else []
            )

            year = _clean_int(row.get(mapping.year_column))
            source = _clean_str(row.get(mapping.source_column))
            original_data = {col: (None if pd.isna(row[col]) else row[col]) for col in df.columns}

            db.insert_document(
                serial_number=serial,
                doc_type=mapping.doc_type,
                title=title,
                abstract=abstract,
                year=year,
                authors=authors,
                source=source,
                original_data=original_data,
                conn=conn,
            )
            imported += 1

    summary = {"imported": imported, "skipped": skipped, "source": csv_path}
    logger.info("%s import: %s", mapping.doc_type.capitalize(), summary)
    return summary


def import_all() -> dict:
    db.init_db()

    papers = import_csv("data/MANI_KW_PAPERS_scopus.csv", PAPER_MAPPING)
    patents_a = import_csv("data/MANI_KW_PATENTS_A_weds1969to2009.csv", PATENT_MAPPING)
    patents_b = import_csv("data/MANI_KW_PATENTS_B_weds2010tonow.csv", PATENT_MAPPING)

    counts = db.count_documents()

    return {
        "papers": papers,
        "patents_a": patents_a,
        "patents_b": patents_b,
        "totals": counts,
    }
