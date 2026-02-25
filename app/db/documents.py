import json
import logging
from typing import Optional

from app.db.connection import transaction

logger = logging.getLogger(__name__)


def insert_document(serial_number: str, doc_type: str, title: str,
                    abstract: str, year: Optional[int], authors: list[str],
                    source: Optional[str], original_data: dict,
                    conn=None):
    """Insert or replace a document. Accepts an optional external connection for batching."""
    def _execute(c):
        c.execute(
            """INSERT OR REPLACE INTO documents
               (serial_number, doc_type, title, abstract, year, authors, source, original_data)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (serial_number, doc_type, title, abstract, year,
             json.dumps(authors), source, json.dumps(original_data, default=str)),
        )

    if conn is not None:
        _execute(conn)
    else:
        with transaction() as c:
            _execute(c)


def get_document(serial_number: str) -> Optional[dict]:
    with transaction() as conn:
        row = conn.execute(
            "SELECT * FROM documents WHERE serial_number = ?", (serial_number,)
        ).fetchone()
        return dict(row) if row else None


def get_documents(doc_type: Optional[str] = None) -> list[dict]:
    with transaction() as conn:
        if doc_type:
            rows = conn.execute(
                "SELECT * FROM documents WHERE doc_type = ? ORDER BY year, serial_number",
                (doc_type,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM documents ORDER BY doc_type, year, serial_number"
            ).fetchall()
        return [dict(r) for r in rows]


def get_documents_paginated(doc_type: Optional[str] = None,
                            limit: int = 100, offset: int = 0) -> tuple[list[dict], int]:
    """Return (rows, total_count) using SQL LIMIT/OFFSET."""
    with transaction() as conn:
        if doc_type:
            total = conn.execute(
                "SELECT COUNT(*) FROM documents WHERE doc_type = ?", (doc_type,)
            ).fetchone()[0]
            rows = conn.execute(
                "SELECT * FROM documents WHERE doc_type = ? ORDER BY year, serial_number LIMIT ? OFFSET ?",
                (doc_type, limit, offset)
            ).fetchall()
        else:
            total = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
            rows = conn.execute(
                "SELECT * FROM documents ORDER BY doc_type, year, serial_number LIMIT ? OFFSET ?",
                (limit, offset)
            ).fetchall()
        return [dict(r) for r in rows], total


def get_unclassified_documents(doc_type: Optional[str] = None) -> list[dict]:
    with transaction() as conn:
        base_query = """SELECT d.* FROM documents d
                        LEFT JOIN classifications c ON d.serial_number = c.serial_number
                        WHERE c.serial_number IS NULL
                          AND d.abstract IS NOT NULL AND d.abstract != ''"""
        if doc_type:
            rows = conn.execute(
                base_query + " AND d.doc_type = ? ORDER BY d.year, d.serial_number",
                (doc_type,)
            ).fetchall()
        else:
            rows = conn.execute(
                base_query + " ORDER BY d.doc_type, d.year, d.serial_number"
            ).fetchall()
        return [dict(r) for r in rows]


def count_documents() -> dict:
    with transaction() as conn:
        total = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        papers = conn.execute("SELECT COUNT(*) FROM documents WHERE doc_type = 'paper'").fetchone()[0]
        patents = conn.execute("SELECT COUNT(*) FROM documents WHERE doc_type = 'patent'").fetchone()[0]
        classified = conn.execute("SELECT COUNT(*) FROM classifications WHERE status != 'pending'").fetchone()[0]
        pending = conn.execute(
            """SELECT COUNT(*) FROM documents d
               LEFT JOIN classifications c ON d.serial_number = c.serial_number
               WHERE c.serial_number IS NULL AND d.abstract IS NOT NULL AND d.abstract != ''"""
        ).fetchone()[0]
        return {
            "total": total, "papers": papers, "patents": patents,
            "classified": classified, "pending": pending,
        }
