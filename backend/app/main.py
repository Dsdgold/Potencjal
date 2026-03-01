from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from app.database import engine, Base
from app.routers import leads, osint, scoring

FRONTEND_PATH = Path(__file__).resolve().parent.parent.parent / "mvp_osint_launcher_szybkie_sprawdzenie_potencjalu_html.html"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup (use Alembic for production migrations)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(
    title="Potencjał API",
    description="Backend do oceny potencjału klientów B2B (materiały budowlane)",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(leads.router)
app.include_router(scoring.router)
app.include_router(osint.router)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    return FRONTEND_PATH.read_text(encoding="utf-8")
