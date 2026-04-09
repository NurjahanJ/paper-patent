import logging
import shutil
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app import db
from app.config import settings
from app.routes import documents, classify, review, analysis, export, graph, progress, review_ui, dashboard

logger = logging.getLogger(__name__)


def seed_database():
    """Copy the baseline database to the persistent disk on first run.
    
    On Render with a persistent disk, DB_PATH points to /data/ferrofluids.db.
    If that file doesn't exist yet, copy the repo's bundled database there.
    This ensures reviews persist across deploys without being overwritten.
    """
    db_path = Path(settings.db_path)
    repo_db = Path(__file__).resolve().parent.parent / "ferrofluids.db"
    
    if db_path.resolve() == repo_db:
        logger.info("Using local database: %s", db_path)
        return
    
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    if not db_path.exists():
        if repo_db.exists():
            logger.info("Seeding database: %s -> %s", repo_db, db_path)
            shutil.copy2(repo_db, db_path)
        else:
            logger.warning("No baseline database found at %s", repo_db)
    else:
        logger.info("Persistent database already exists: %s", db_path)


@asynccontextmanager
async def lifespan(application: FastAPI):
    seed_database()
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
