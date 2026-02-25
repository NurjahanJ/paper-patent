import logging
import sqlite3
from contextlib import contextmanager

from app.config import settings

logger = logging.getLogger(__name__)


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def transaction():
    """Context manager that provides a connection with automatic commit/rollback."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with transaction() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS documents (
                serial_number TEXT PRIMARY KEY,
                doc_type TEXT NOT NULL,
                title TEXT,
                abstract TEXT,
                year INTEGER,
                authors TEXT,
                source TEXT,
                original_data TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS classifications (
                serial_number TEXT PRIMARY KEY,
                final_primary INTEGER,
                final_secondary INTEGER,
                final_tertiary INTEGER,
                final_reasoning TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                FOREIGN KEY (serial_number) REFERENCES documents(serial_number)
            );

            CREATE TABLE IF NOT EXISTS ai_results (
                serial_number TEXT NOT NULL,
                model_name TEXT NOT NULL,
                primary_code INTEGER,
                secondary_code INTEGER,
                tertiary_code INTEGER,
                reasoning TEXT,
                PRIMARY KEY (serial_number, model_name),
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
            CREATE INDEX IF NOT EXISTS idx_ai_results_serial ON ai_results(serial_number);
        """)
    logger.info("Database initialized: %s", settings.db_path)
