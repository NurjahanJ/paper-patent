import json
import logging
from collections import defaultdict

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app import db
from app.db.connection import transaction

logger = logging.getLogger(__name__)


def link_patents_to_papers(top_n: int = 3) -> dict:
    """
    Goal 3 (part 2): For each patent, find at least 3 related papers
    based on abstract similarity using TF-IDF cosine similarity.
    """
    with transaction() as conn:
        patents = conn.execute(
            """SELECT d.serial_number, d.abstract
               FROM documents d
               JOIN classifications c ON d.serial_number = c.serial_number
               WHERE d.doc_type = 'patent' AND c.status IN ('agreed', 'human_reviewed')
               AND d.abstract IS NOT NULL AND d.abstract != ''"""
        ).fetchall()

        papers = conn.execute(
            """SELECT d.serial_number, d.abstract
               FROM documents d
               JOIN classifications c ON d.serial_number = c.serial_number
               WHERE d.doc_type = 'paper' AND c.status IN ('agreed', 'human_reviewed')
               AND d.abstract IS NOT NULL AND d.abstract != ''"""
        ).fetchall()

    patents = [dict(r) for r in patents]
    papers = [dict(r) for r in papers]

    if not patents or not papers:
        logger.warning("Not enough classified documents for linking. Patents: %d, Papers: %d",
                       len(patents), len(papers))
        return {"linked": 0, "total_patents": len(patents), "total_papers": len(papers)}

    logger.info("Computing TF-IDF similarity: %d patents x %d papers", len(patents), len(papers))

    all_abstracts = [p["abstract"] for p in papers] + [p["abstract"] for p in patents]
    paper_serials = [p["serial_number"] for p in papers]
    patent_serials = [p["serial_number"] for p in patents]

    vectorizer = TfidfVectorizer(max_features=10000, stop_words="english")
    tfidf_matrix = vectorizer.fit_transform(all_abstracts)

    paper_matrix = tfidf_matrix[:len(papers)]
    patent_matrix = tfidf_matrix[len(papers):]

    # Compute similarity in batches to avoid memory issues
    linked = 0
    batch_size = 100

    for i in range(0, len(patent_serials), batch_size):
        batch_end = min(i + batch_size, len(patent_serials))
        batch_patents = patent_matrix[i:batch_end]

        sim_matrix = cosine_similarity(batch_patents, paper_matrix)

        link_rows = []
        for j, patent_idx in enumerate(range(i, batch_end)):
            scores = sim_matrix[j]
            top_indices = scores.argsort()[-top_n:][::-1]

            for paper_idx in top_indices:
                score = float(scores[paper_idx])
                if score > 0:
                    link_rows.append((
                        patent_serials[patent_idx],
                        paper_serials[paper_idx],
                        round(score, 4),
                    ))
                    linked += 1

        # Batch write per chunk
        if link_rows:
            db.save_paper_patent_links_batch(link_rows)

        if batch_end % 200 == 0 or batch_end == len(patent_serials):
            logger.info("Linking progress: %d/%d patents processed", batch_end, len(patent_serials))

    result = {"linked": linked, "total_patents": len(patents), "total_papers": len(papers)}
    logger.info("Paper-patent linking complete: %s", result)
    return result


def crossref_assignees() -> dict:
    """
    Goal 4: Find patent assignees/inventors who also published papers.
    Match by normalized name comparison.
    """
    with transaction() as conn:
        patents = conn.execute(
            """SELECT d.serial_number, d.authors, d.original_data,
                      c.final_primary
               FROM documents d
               JOIN classifications c ON d.serial_number = c.serial_number
               WHERE d.doc_type = 'patent' AND c.status IN ('agreed', 'human_reviewed')"""
        ).fetchall()

        papers = conn.execute(
            """SELECT d.serial_number, d.authors, c.final_primary
               FROM documents d
               JOIN classifications c ON d.serial_number = c.serial_number
               WHERE d.doc_type = 'paper' AND c.status IN ('agreed', 'human_reviewed')"""
        ).fetchall()

    patents = [dict(r) for r in patents]
    papers = [dict(r) for r in papers]

    if not patents or not papers:
        return {"matches": 0}

    # Build paper author index: normalized_name -> [(serial, primary_class)]
    paper_author_index = defaultdict(list)
    for paper in papers:
        authors = json.loads(paper["authors"]) if paper["authors"] else []
        primary = paper["final_primary"]
        for author in authors:
            norm = _normalize_name(author)
            if norm and len(norm) > 2:
                paper_author_index[norm].append((paper["serial_number"], primary))

    matches = 0
    for patent in patents:
        inventors = json.loads(patent["authors"]) if patent["authors"] else []
        # Also check applicants/owners from original data
        original = json.loads(patent["original_data"]) if patent["original_data"] else {}
        applicants_raw = original.get("Applicants", "") or ""
        owners_raw = original.get("Owners", "") or ""

        all_names = list(inventors)
        for extra in [applicants_raw, owners_raw]:
            if extra:
                all_names.extend([n.strip() for n in str(extra).split(";") if n.strip()])

        patent_primary = patent["final_primary"]

        for name in all_names:
            norm = _normalize_name(name)
            if norm and norm in paper_author_index:
                for paper_serial, paper_primary in paper_author_index[norm]:
                    # Match if same primary class (same topic)
                    if paper_primary == patent_primary:
                        db.save_assignee_crossref(
                            patent["serial_number"], paper_serial, name.strip()
                        )
                        matches += 1

    result = {"matches": matches, "patents_checked": len(patents), "papers_checked": len(papers)}
    logger.info("Assignee cross-reference complete: %s", result)
    return result


def _normalize_name(name: str) -> str:
    """Normalize a name for comparison: lowercase, strip, remove extra whitespace."""
    if not name:
        return ""
    parts = name.strip().lower().split(",")
    # Handle "Last, First" format — normalize to "first last"
    if len(parts) == 2:
        return f"{parts[1].strip()} {parts[0].strip()}"
    return " ".join(name.strip().lower().split())
