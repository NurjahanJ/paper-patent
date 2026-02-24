from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import classify, review, graph

app = FastAPI(
    title="Paper-Patent Classifier",
    description="AI-assisted system for classifying patents and research abstracts using dual AI models (GPT + Claude) with consensus-based validation and knowledge graph visualization.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(classify.router)
app.include_router(review.router)
app.include_router(graph.router)


@app.get("/")
async def root():
    return {
        "name": "Paper-Patent Classifier",
        "version": "1.0.0",
        "endpoints": {
            "docs": "/docs",
            "documents": "/documents",
            "classify": "/documents/classify",
            "review_pending": "/review/pending",
            "resolve_review": "/review/resolve",
            "knowledge_graph": "/graph/generate",
        },
    }
