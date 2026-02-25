import logging
from typing import Optional

from app.db.connection import transaction

logger = logging.getLogger(__name__)


def save_ai_result(serial_number: str, model_name: str,
                   primary: int, secondary: int, tertiary: int,
                   reasoning: str, conn=None):
    """Save a single AI model's classification result. OCP-compliant: any model name works."""
    def _execute(c):
        c.execute(
            """INSERT OR REPLACE INTO ai_results
               (serial_number, model_name, primary_code, secondary_code, tertiary_code, reasoning)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (serial_number, model_name, primary, secondary, tertiary, reasoning),
        )
        # Ensure classification row exists
        c.execute(
            "INSERT OR IGNORE INTO classifications (serial_number, status) VALUES (?, 'pending')",
            (serial_number,)
        )

    if conn is not None:
        _execute(conn)
    else:
        with transaction() as c:
            _execute(c)


def finalize_classification(serial_number: str, primary: int, secondary: int,
                            tertiary: int, reasoning: str, status: str, conn=None):
    def _execute(c):
        c.execute(
            """UPDATE classifications
               SET final_primary=?, final_secondary=?, final_tertiary=?,
                   final_reasoning=?, status=?
               WHERE serial_number=?""",
            (primary, secondary, tertiary, reasoning, status, serial_number),
        )

    if conn is not None:
        _execute(conn)
    else:
        with transaction() as c:
            _execute(c)


def get_classification(serial_number: str) -> Optional[dict]:
    with transaction() as conn:
        row = conn.execute(
            """SELECT c.*, 
                      gpt.primary_code AS gpt_primary, gpt.reasoning AS gpt_reasoning,
                      claude.primary_code AS claude_primary, claude.reasoning AS claude_reasoning
               FROM classifications c
               LEFT JOIN ai_results gpt ON c.serial_number = gpt.serial_number AND gpt.model_name = 'gpt'
               LEFT JOIN ai_results claude ON c.serial_number = claude.serial_number AND claude.model_name = 'claude'
               WHERE c.serial_number = ?""",
            (serial_number,)
        ).fetchone()
        return dict(row) if row else None


def get_classifications_by_status(status: str) -> list[dict]:
    with transaction() as conn:
        rows = conn.execute(
            "SELECT * FROM classifications WHERE status = ?", (status,)
        ).fetchall()
        return [dict(r) for r in rows]


def get_all_classified() -> list[dict]:
    with transaction() as conn:
        rows = conn.execute(
            """SELECT d.*, c.final_primary, c.final_secondary, c.final_tertiary,
                      c.final_reasoning, c.status,
                      gpt.primary_code AS gpt_primary, gpt.reasoning AS gpt_reasoning,
                      claude.primary_code AS claude_primary, claude.reasoning AS claude_reasoning
               FROM documents d
               JOIN classifications c ON d.serial_number = c.serial_number
               LEFT JOIN ai_results gpt ON d.serial_number = gpt.serial_number AND gpt.model_name = 'gpt'
               LEFT JOIN ai_results claude ON d.serial_number = claude.serial_number AND claude.model_name = 'claude'
               WHERE c.status IN ('agreed', 'human_reviewed')
               ORDER BY d.year, c.final_primary, c.final_secondary, c.final_tertiary"""
        ).fetchall()
        return [dict(r) for r in rows]
