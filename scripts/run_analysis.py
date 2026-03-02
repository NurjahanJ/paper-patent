"""Run all analysis, exports, and knowledge graph generation."""
from app import db
from app.services.gap_analysis import gap_summary, gap_by_five_year_periods
from app.services.linking import link_patents_to_papers, crossref_assignees
from app.services.export import (
    export_classified_papers, export_classified_patents,
    export_gap_analysis, export_patent_paper_links,
    export_assignee_crossrefs,
)
from app.services.knowledge_graph import generate_graph_html

db.init_db()

# Goal 3a: Gap analysis
print("=== Gap Analysis ===")
gaps = gap_summary()
print(f"Papers classified: {gaps['total_papers_classified']}")
print(f"Patents classified: {gaps['total_patents_classified']}")
print(f"Classes with no patents: {gaps['classes_with_no_patents']}")
print(f"Classes with no papers: {gaps['classes_with_no_papers']}")
print()

# Goal 3b: Patent-paper linking
print("=== Patent-Paper Linking ===")
link_result = link_patents_to_papers(top_n=3)
print(link_result)
print()

# Goal 4: Assignee cross-reference
print("=== Assignee Cross-Reference ===")
crossref_result = crossref_assignees()
print(crossref_result)
print()

# Export all CSVs
print("=== Exporting CSVs ===")
print("Papers:", export_classified_papers())
print("Patents:", export_classified_patents())
print("Gaps:", export_gap_analysis())
print("Links:", export_patent_paper_links())
print("Crossrefs:", export_assignee_crossrefs())

# Knowledge graph
print()
print("=== Knowledge Graph ===")
html = generate_graph_html(include_docs=False)
with open("output/knowledge_graph.html", "w", encoding="utf-8") as f:
    f.write(html)
print("Saved to output/knowledge_graph.html")
print()
print("DONE - All analysis and exports complete!")
