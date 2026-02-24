from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from app.models.schemas import ClassificationStatus, GraphSettings
from app.services.knowledge_graph import generate_html
from app.services.storage import load_documents

router = APIRouter(prefix="/graph", tags=["graph"])


@router.post("/generate", response_class=HTMLResponse)
async def generate_knowledge_graph(graph_settings: GraphSettings | None = None):
    documents = load_documents()

    classified = [
        d
        for d in documents
        if d.status in (ClassificationStatus.AGREED, ClassificationStatus.HUMAN_REVIEWED)
        and d.final_classification is not None
    ]

    if not classified:
        return HTMLResponse(
            content="<h2>No classified documents available. Please classify documents first.</h2>",
            status_code=200,
        )

    output_path = "knowledge_graph.html"
    generate_html(classified, output_path, graph_settings)

    with open(output_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    return HTMLResponse(content=html_content)
