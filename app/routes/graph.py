from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from app.services.knowledge_graph import generate_graph_html

router = APIRouter(prefix="/graph", tags=["graph"])


@router.get("/", response_class=HTMLResponse)
async def get_knowledge_graph(include_docs: bool = False):
    """
    Generate and return the knowledge graph as interactive HTML.
    - include_docs=False: shows only category nodes and co-occurrence edges
    - include_docs=True: also shows individual document nodes (can be slow with many docs)
    """
    html = generate_graph_html(include_docs=include_docs)
    return HTMLResponse(content=html)
