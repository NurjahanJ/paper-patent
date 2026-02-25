from app.db.connection import get_connection, transaction, init_db
from app.db.documents import (
    insert_document,
    get_document,
    get_documents,
    get_documents_paginated,
    get_unclassified_documents,
    count_documents,
)
from app.db.classifications import (
    save_ai_result,
    finalize_classification,
    get_classification,
    get_classifications_by_status,
    get_all_classified,
)
from app.db.links import (
    save_paper_patent_link,
    save_paper_patent_links_batch,
    save_assignee_crossref,
    get_links_for_patent,
    get_crossrefs_for_patent,
)

__all__ = [
    "get_connection",
    "transaction",
    "init_db",
    "insert_document",
    "get_document",
    "get_documents",
    "get_documents_paginated",
    "get_unclassified_documents",
    "count_documents",
    "save_ai_result",
    "finalize_classification",
    "get_classification",
    "get_classifications_by_status",
    "get_all_classified",
    "save_paper_patent_link",
    "save_paper_patent_links_batch",
    "save_assignee_crossref",
    "get_links_for_patent",
    "get_crossrefs_for_patent",
]
