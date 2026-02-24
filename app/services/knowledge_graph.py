import networkx as nx
from pyvis.network import Network

from app.models.schemas import Document, GraphSettings


def build_graph(documents: list[Document], graph_settings: GraphSettings | None = None) -> nx.Graph:
    if graph_settings is None:
        graph_settings = GraphSettings()

    G = nx.Graph()

    for doc in documents:
        if not doc.final_classification:
            continue

        node_color = "#4CAF50" if doc.doc_type.value == "patent" else "#2196F3"
        node_shape = "diamond" if doc.doc_type.value == "patent" else "dot"

        G.add_node(
            doc.id,
            label=doc.title[:50] + ("..." if len(doc.title) > 50 else ""),
            title=f"{doc.title}\n\nType: {doc.doc_type.value}\nCategory: {doc.final_classification.category}\nConfidence: {doc.final_classification.confidence}",
            color=node_color,
            shape=node_shape,
            group=doc.final_classification.category,
        )

        if graph_settings.show_categories:
            cat_id = f"cat_{doc.final_classification.category}"
            if cat_id not in G:
                G.add_node(
                    cat_id,
                    label=doc.final_classification.category,
                    title=f"Category: {doc.final_classification.category}",
                    color="#FF9800",
                    shape="square",
                    size=30,
                )
            G.add_edge(doc.id, cat_id, color="#cccccc")

        if graph_settings.show_keywords:
            for kw in doc.final_classification.keywords:
                kw_id = f"kw_{kw.lower()}"
                if kw_id not in G:
                    G.add_node(
                        kw_id,
                        label=kw,
                        title=f"Keyword: {kw}",
                        color="#9C27B0",
                        shape="triangle",
                        size=15,
                    )
                G.add_edge(doc.id, kw_id, color="#eeeeee")

    return G


def generate_html(
    documents: list[Document],
    output_path: str = "knowledge_graph.html",
    graph_settings: GraphSettings | None = None,
) -> str:
    if graph_settings is None:
        graph_settings = GraphSettings()

    G = build_graph(documents, graph_settings)

    net = Network(
        height=graph_settings.height,
        width=graph_settings.width,
        bgcolor="#ffffff",
        font_color="#333333",
        directed=False,
    )

    net.from_nx(G)

    net.set_options("""
    {
        "physics": {
            "forceAtlas2Based": {
                "gravitationalConstant": -50,
                "centralGravity": 0.01,
                "springLength": 200,
                "springConstant": 0.08
            },
            "solver": "forceAtlas2Based",
            "stabilization": {
                "iterations": 150
            }
        },
        "interaction": {
            "hover": true,
            "tooltipDelay": 200
        }
    }
    """)

    net.save_graph(output_path)
    return output_path
