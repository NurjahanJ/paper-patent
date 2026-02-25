import logging

from app.db.connection import transaction

logger = logging.getLogger(__name__)


def save_paper_patent_link(patent_serial: str, paper_serial: str, score: float, conn=None):
    def _execute(c):
        c.execute(
            "INSERT OR REPLACE INTO paper_patent_links VALUES (?, ?, ?)",
            (patent_serial, paper_serial, score),
        )

    if conn is not None:
        _execute(conn)
    else:
        with transaction() as c:
            _execute(c)


def save_paper_patent_links_batch(links: list[tuple[str, str, float]]):
    """Batch insert patent-paper links in a single transaction."""
    with transaction() as conn:
        conn.executemany(
            "INSERT OR REPLACE INTO paper_patent_links VALUES (?, ?, ?)",
            links,
        )


def save_assignee_crossref(patent_serial: str, paper_serial: str, matched_name: str, conn=None):
    def _execute(c):
        c.execute(
            "INSERT OR REPLACE INTO assignee_crossrefs VALUES (?, ?, ?)",
            (patent_serial, paper_serial, matched_name),
        )

    if conn is not None:
        _execute(conn)
    else:
        with transaction() as c:
            _execute(c)


def get_links_for_patent(patent_serial: str) -> list[dict]:
    with transaction() as conn:
        rows = conn.execute(
            """SELECT l.paper_serial, l.similarity_score, d.title, d.year
               FROM paper_patent_links l
               JOIN documents d ON l.paper_serial = d.serial_number
               WHERE l.patent_serial = ?
               ORDER BY l.similarity_score DESC""",
            (patent_serial,)
        ).fetchall()
        return [dict(r) for r in rows]


def get_crossrefs_for_patent(patent_serial: str) -> list[dict]:
    with transaction() as conn:
        rows = conn.execute(
            """SELECT a.paper_serial, a.matched_name, d.title, d.year
               FROM assignee_crossrefs a
               JOIN documents d ON a.paper_serial = d.serial_number
               WHERE a.patent_serial = ?""",
            (patent_serial,)
        ).fetchall()
        return [dict(r) for r in rows]
