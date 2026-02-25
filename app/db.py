import json
import logging
import sqlite3
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = get_connection()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS documents (
                serial_number TEXT PRIMARY KEY,
                doc_type TEXT NOT NULL,          -- 'paper' or 'patent'
                title TEXT,
                abstract TEXT,
                year INTEGER,
                authors TEXT,                    -- JSON array
                source TEXT,
                original_data TEXT NOT NULL       -- full original row as JSON
            );

            CREATE TABLE IF NOT EXISTS classifications (
                serial_number TEXT PRIMARY KEY,
                gpt_primary INTEGER,
                gpt_secondary INTEGER,
                gpt_tertiary INTEGER,
                gpt_reasoning TEXT,
                claude_primary INTEGER,
                claude_secondary INTEGER,
                claude_tertiary INTEGER,
                claude_reasoning TEXT,
                final_primary INTEGER,
                final_secondary INTEGER,
                final_tertiary INTEGER,
                final_reasoning TEXT,
                status TEXT NOT NULL DEFAULT 'pending',  -- pending, agreed, disagreed, human_reviewed
                FOREIGN KEY (serial_number) REFERENCES documents(serial_number)
            );

            CREATE TABLE IF NOT EXISTS paper_patent_links (
                patent_serial TEXT NOT NULL,
                paper_serial TEXT NOT NULL,
                similarity_score REAL,
                PRIMARY KEY (patent_serial, paper_serial),
                FOREIGN KEY (patent_serial) REFERENCES documents(serial_number),
                FOREIGN KEY (paper_serial) REFERENCES documents(serial_number)
            );

            CREATE TABLE IF NOT EXISTS assignee_crossrefs (
                patent_serial TEXT NOT NULL,
                paper_serial TEXT NOT NULL,
                matched_name TEXT,
                PRIMARY KEY (patent_serial, paper_serial),
                FOREIGN KEY (patent_serial) REFERENCES documents(serial_number),
                FOREIGN KEY (paper_serial) REFERENCES documents(serial_number)
            );

            CREATE INDEX IF NOT EXISTS idx_doc_type ON documents(doc_type);
            CREATE INDEX IF NOT EXISTS idx_doc_year ON documents(year);
            CREATE INDEX IF NOT EXISTS idx_class_status ON classifications(status);
            CREATE INDEX IF NOT EXISTS idx_class_primary ON classifications(final_primary);
        """)
        conn.commit()
        logger.info("Database initialized: %s", settings.db_path)
    finally:
        conn.close()


# --- Document CRUD ---

def insert_document(serial_number: str, doc_type: str, title: str,
                    abstract: str, year: Optional[int], authors: list[str],
                    source: Optional[str], original_data: dict):
    conn = get_connection()
    try:
        conn.execute(
            """INSERT OR REPLACE INTO documents
               (serial_number, doc_type, title, abstract, year, authors, source, original_data)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (serial_number, doc_type, title, abstract, year,
             json.dumps(authors), source, json.dumps(original_data, default=str)),
        )
        conn.commit()
    finally:
        conn.close()


def get_document(serial_number: str) -> Optional[dict]:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM documents WHERE serial_number = ?", (serial_number,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_documents(doc_type: Optional[str] = None) -> list[dict]:
    conn = get_connection()
    try:
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
    finally:
        conn.close()


def get_unclassified_documents(doc_type: Optional[str] = None) -> list[dict]:
    conn = get_connection()
    try:
        if doc_type:
            rows = conn.execute(
                """SELECT d.* FROM documents d
                   LEFT JOIN classifications c ON d.serial_number = c.serial_number
                   WHERE c.serial_number IS NULL AND d.doc_type = ? AND d.abstract IS NOT NULL AND d.abstract != ''
                   ORDER BY d.year, d.serial_number""",
                (doc_type,)
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT d.* FROM documents d
                   LEFT JOIN classifications c ON d.serial_number = c.serial_number
                   WHERE c.serial_number IS NULL AND d.abstract IS NOT NULL AND d.abstract != ''
                   ORDER BY d.doc_type, d.year, d.serial_number"""
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def count_documents() -> dict:
    conn = get_connection()
    try:
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
    finally:
        conn.close()


# --- Classification CRUD ---

def save_classification(serial_number: str, model: str,
                        primary: int, secondary: int, tertiary: int,
                        reasoning: str):
    conn = get_connection()
    try:
        # Ensure row exists
        conn.execute(
            "INSERT OR IGNORE INTO classifications (serial_number, status) VALUES (?, 'pending')",
            (serial_number,)
        )
        if model == "gpt":
            conn.execute(
                """UPDATE classifications
                   SET gpt_primary=?, gpt_secondary=?, gpt_tertiary=?, gpt_reasoning=?
                   WHERE serial_number=?""",
                (primary, secondary, tertiary, reasoning, serial_number),
            )
        elif model == "claude":
            conn.execute(
                """UPDATE classifications
                   SET claude_primary=?, claude_secondary=?, claude_tertiary=?, claude_reasoning=?
                   WHERE serial_number=?""",
                (primary, secondary, tertiary, reasoning, serial_number),
            )
        conn.commit()
    finally:
        conn.close()


def finalize_classification(serial_number: str, primary: int, secondary: int,
                            tertiary: int, reasoning: str, status: str):
    conn = get_connection()
    try:
        conn.execute(
            """UPDATE classifications
               SET final_primary=?, final_secondary=?, final_tertiary=?,
                   final_reasoning=?, status=?
               WHERE serial_number=?""",
            (primary, secondary, tertiary, reasoning, status, serial_number),
        )
        conn.commit()
    finally:
        conn.close()


def get_classification(serial_number: str) -> Optional[dict]:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM classifications WHERE serial_number = ?", (serial_number,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_classifications_by_status(status: str) -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM classifications WHERE status = ?", (status,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_all_classified() -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT d.*, c.final_primary, c.final_secondary, c.final_tertiary,
                      c.final_reasoning, c.status, c.gpt_primary, c.gpt_reasoning,
                      c.claude_primary, c.claude_reasoning
               FROM documents d
               JOIN classifications c ON d.serial_number = c.serial_number
               WHERE c.status IN ('agreed', 'human_reviewed')
               ORDER BY d.year, c.final_primary, c.final_secondary, c.final_tertiary"""
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# --- Links ---

def save_paper_patent_link(patent_serial: str, paper_serial: str, score: float):
    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO paper_patent_links VALUES (?, ?, ?)",
            (patent_serial, paper_serial, score),
        )
        conn.commit()
    finally:
        conn.close()


def save_assignee_crossref(patent_serial: str, paper_serial: str, matched_name: str):
    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO assignee_crossrefs VALUES (?, ?, ?)",
            (patent_serial, paper_serial, matched_name),
        )
        conn.commit()
    finally:
        conn.close()


def get_links_for_patent(patent_serial: str) -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT l.paper_serial, l.similarity_score, d.title, d.year
               FROM paper_patent_links l
               JOIN documents d ON l.paper_serial = d.serial_number
               WHERE l.patent_serial = ?
               ORDER BY l.similarity_score DESC""",
            (patent_serial,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_crossrefs_for_patent(patent_serial: str) -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT a.paper_serial, a.matched_name, d.title, d.year
               FROM assignee_crossrefs a
               JOIN documents d ON a.paper_serial = d.serial_number
               WHERE a.patent_serial = ?""",
            (patent_serial,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
