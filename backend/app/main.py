from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from sqlalchemy import select

from app.config import settings
from app.database import async_session, engine, Base
from app.models import User
from app.routers import auth, leads, osint, scoring
from app.services.auth import hash_password

_FNAME = "mvp_osint_launcher_szybkie_sprawdzenie_potencjalu_html.html"
_CANDIDATES = [
    Path(__file__).resolve().parent.parent.parent / _FNAME,   # repo layout
    Path("/var/www/html") / _FNAME,                           # server layout
]
FRONTEND_PATH = next((p for p in _CANDIDATES if p.exists()), _CANDIDATES[0])


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup (use Alembic for production migrations)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create default admin if no users exist
    async with async_session() as db:
        result = await db.execute(select(User).limit(1))
        if not result.scalar_one_or_none():
            admin = User(
                email=settings.admin_email,
                password_hash=hash_password(settings.admin_password),
                full_name="Administrator",
                role="admin",
                package="enterprise",
            )
            db.add(admin)
            await db.commit()
    yield


app = FastAPI(
    title="Potencjal API",
    description="Backend do oceny potencjalu klientów B2B (materialy budowlane)",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(leads.router)
app.include_router(scoring.router)
app.include_router(osint.router)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    if not FRONTEND_PATH.exists():
        return HTMLResponse("<h1>Frontend not found</h1>", status_code=404)
    return FRONTEND_PATH.read_text(encoding="utf-8")
