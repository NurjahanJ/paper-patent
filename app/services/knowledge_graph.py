import logging
import os
import tempfile

import networkx as nx
from pyvis.network import Network

from app.db.connection import transaction
from app.taxonomy import TAXONOMY

logger = logging.getLogger(__name__)

# Colors for major categories
CATEGORY_COLORS = {
    "Material": "#4CAF50",
    "Computation": "#2196F3",
    "Experimentation": "#FF9800",
    "Application": "#E91E63",
    "Review / Book": "#9C27B0",
}

DOC_TYPE_COLORS = {
    "paper": "#42A5F5",
    "patent": "#66BB6A",
}


def build_graph(include_docs: bool = False) -> nx.Graph:
    """
    Build a knowledge graph showing:
    - Category nodes (class codes)
    - Edges between categories weighted by co-occurrence
    - Optionally: document nodes connected to their primary class
    - Gap highlighting: categories with no patents shown differently
    """
    graph = nx.Graph()

    with transaction() as conn:
        # Get classification counts per class per doc_type
        rows = conn.execute(
            """SELECT d.doc_type, c.final_primary, COUNT(*) as cnt
               FROM documents d
               JOIN classifications c ON d.serial_number = c.serial_number
               WHERE c.status IN ('agreed', 'human_reviewed')
               GROUP BY d.doc_type, c.final_primary"""
        ).fetchall()

        # Get co-occurrence edges (docs that share secondary/tertiary classes)
        cooccurrence = conn.execute(
            """SELECT c.final_primary, c.final_secondary, COUNT(*) as cnt
               FROM classifications c
               WHERE c.status IN ('agreed', 'human_reviewed')
                 AND c.final_primary != c.final_secondary
               GROUP BY c.final_primary, c.final_secondary
               HAVING cnt >= 2"""
        ).fetchall()

        docs = []
        if include_docs:
            docs = conn.execute(
                """SELECT d.serial_number, d.title, d.doc_type, d.year,
                          c.final_primary
                   FROM documents d
                   JOIN classifications c ON d.serial_number = c.serial_number
                   WHERE c.status IN ('agreed', 'human_reviewed')"""
            ).fetchall()

    # Build class code nodes
    paper_counts = {}
    patent_counts = {}
    for row in rows:
        code = row["final_primary"]
        if row["doc_type"] == "paper":
            paper_counts[code] = row["cnt"]
        else:
            patent_counts[code] = row["cnt"]

    for code, cls in TAXONOMY.items():
        papers = paper_counts.get(code, 0)
        patents = patent_counts.get(code, 0)
        total = papers + patents

        if total == 0:
            continue

        is_gap = patents == 0 and papers > 0
        color = "#FF5252" if is_gap else CATEGORY_COLORS.get(cls.major_category, "#999")

        graph.add_node(
            f"class_{code}",
            label=f"{code}",
            title=(
                f"Class {code}: {cls.description}\n"
                f"Category: {cls.major_category}\n"
                f"Papers: {papers} | Patents: {patents}\n"
                f"{'⚠ GAP: No patents in this class!' if is_gap else ''}"
            ),
            color=color,
            size=15 + min(total, 100),
            shape="square",
            group=cls.major_category,
        )

    # Add co-occurrence edges
    for row in cooccurrence:
        src = f"class_{row['final_primary']}"
        dst = f"class_{row['final_secondary']}"
        if src in graph and dst in graph:
            graph.add_edge(src, dst, weight=row["cnt"], color="#cccccc",
                           title=f"Co-occurrence: {row['cnt']} documents")

    # Optionally add document nodes
    if include_docs:
        for doc in docs:
            doc = dict(doc)
            doc_color = DOC_TYPE_COLORS.get(doc["doc_type"], "#999")
            title_short = doc["title"][:60] + "..." if len(doc["title"]) > 60 else doc["title"]
            graph.add_node(
                doc["serial_number"],
                label=title_short,
                title=f"{doc['title']}\nType: {doc['doc_type']}\nYear: {doc['year']}",
                color=doc_color,
                size=5,
                shape="dot" if doc["doc_type"] == "paper" else "diamond",
            )
            class_node = f"class_{doc['final_primary']}"
            if class_node in graph:
                graph.add_edge(doc["serial_number"], class_node, color="#eeeeee")

    return graph


GRAPH_OPTIONS = """{
    "physics": {
        "forceAtlas2Based": {
            "gravitationalConstant": -100,
            "centralGravity": 0.015,
            "springLength": 200,
            "springConstant": 0.08
        },
        "solver": "forceAtlas2Based",
        "stabilization": { "iterations": 200 }
    },
    "interaction": { "hover": true, "tooltipDelay": 200 }
}"""


def generate_graph_html(include_docs: bool = False) -> str:
    graph = build_graph(include_docs=include_docs)

    net = Network(
        height="900px",
        width="100%",
        bgcolor="#ffffff",
        font_color="#333333",
        directed=False,
    )
    net.from_nx(graph)
    net.set_options(GRAPH_OPTIONS)

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".html", delete=False, encoding="utf-8"
    ) as tmp:
        net.save_graph(tmp.name)
        tmp_path = tmp.name

    with open(tmp_path, "r", encoding="utf-8") as f:
        html = f.read()

    os.unlink(tmp_path)
    return html
