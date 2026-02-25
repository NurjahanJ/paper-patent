from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import documents, classify, review, analysis, export, graph

app = FastAPI(
    title="Ferrofluid Paper-Patent Classifier",
    description="AI-assisted classification of ferrofluid research papers and patents with gap analysis",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents.router)
app.include_router(classify.router)
app.include_router(review.router)
app.include_router(analysis.router)
app.include_router(export.router)
app.include_router(graph.router)


@app.get("/")
async def root():
    from app import db
    db.init_db()
    counts = db.count_documents()
    return {
        "name": "Ferrofluid Paper-Patent Classifier",
        "version": "2.0.0",
        "status": "running",
        "counts": counts,
    }
