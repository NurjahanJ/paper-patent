from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app import db
from app.routes import documents, classify, review, analysis, export, graph, progress, review_ui, dashboard


@asynccontextmanager
async def lifespan(application: FastAPI):
    db.init_db()
    yield


app = FastAPI(
    title="Ferrofluid Paper-Patent Classifier",
    description="AI-assisted classification of ferrofluid research papers and patents with gap analysis",
    version="2.0.0",
    lifespan=lifespan,
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
app.include_router(progress.router)
app.include_router(review_ui.router)
app.include_router(dashboard.router)


@app.get("/")
async def root():
    return RedirectResponse(url="/dashboard")
