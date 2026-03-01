# CLAUDE.md

## Project Overview

**Potencjal** is a B2B sales lead assessment platform for the Polish construction materials sector. It scores client potential using weighted heuristics and OSINT data from public registries.

Two components:
- **Frontend** — standalone HTML file with offline scoring (`mvp_osint_launcher_szybkie_sprawdzenie_potencjalu_html.html`)
- **Backend** — Python/FastAPI API with PostgreSQL, full CRUD, scoring engine, and OSINT proxy to Polish public registries (eKRS, CEIDG, GUS, VAT White List)

## Repository Structure

```
.
├── mvp_osint_launcher_szybkie_sprawdzenie_potencjalu_html.html  # Frontend (HTML + CSS + JS)
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry point
│   │   ├── config.py            # Settings (env vars)
│   │   ├── database.py          # SQLAlchemy async engine
│   │   ├── models.py            # Lead, ScoringHistory models
│   │   ├── schemas.py           # Pydantic request/response schemas
│   │   ├── routers/
│   │   │   ├── leads.py         # CRUD: /api/leads
│   │   │   ├── scoring.py       # /api/scoring
│   │   │   └── osint.py         # /api/osint
│   │   └── services/
│   │       ├── scoring.py       # Scoring engine (ported from JS)
│   │       └── osint.py         # OSINT proxy (VAT, eKRS, CEIDG, GUS)
│   ├── alembic/                 # DB migrations
│   │   ├── env.py
│   │   └── versions/001_initial_tables.py
│   ├── alembic.ini
│   ├── docker-compose.yml       # PostgreSQL
│   ├── requirements.txt
│   ├── .env.example
│   └── .gitignore
├── README.md                    # Polish-language usage docs (git patch)
├── scripts                      # Git patch: setup_github_remote.sh
├── 2                            # Git patch: enrichment improvements
├── .github/workflows/main.yml   # GitHub Actions SSH deployment
└── CLAUDE.md                    # This file
```

**Note:** `README.md`, `scripts`, and `2` are stored as git-apply patch files, not standard files.

## Technology Stack

### Frontend
- **HTML5** with semantic structure, Polish language (`lang="pl"`)
- **CSS3** — CSS variables for dark theme, Grid/Flexbox layout, responsive (`@media` at 900px)
- **Vanilla JavaScript** (ES2020+) — no frameworks, no libraries, no CDN dependencies
- Zero external dependencies. Runs fully offline in any modern browser.

### Backend
- **Python 3.11+** with **FastAPI** (async)
- **PostgreSQL 16** via **SQLAlchemy 2.0** (async with asyncpg)
- **Alembic** for database migrations
- **httpx** for async HTTP calls to OSINT APIs
- **Pydantic v2** for data validation
- **Docker Compose** for local PostgreSQL

## Application Architecture

The HTML file contains three embedded sections:

### CSS (lines 7–43)
- Dark theme via CSS variables (`:root` — `--bg`, `--card`, `--accent`, etc.)
- Grid-based layout with `.grid-4`, `.grid-6`, `.grid-12` column spans
- Responsive: all columns collapse to full-width below 900px

### HTML (lines 45–151)
- Input form: NIP/company name, city, basket value (PLN)
- OSINT launcher buttons (Google searches for LinkedIn, eKRS, CEIDG, etc.)
- OSINT paste textarea for manual data entry
- Output sections: score/tier, recommended actions, firmography table, offer matching, config editor, CSV export

### JavaScript (lines 153–460)
Organized into these modules:

| Module | Key Functions | Purpose |
|--------|--------------|---------|
| Configuration | `CONFIG` object | Scoring weights, revenue bands, PKD mappings, ARPU model |
| Mock Enrichment | `mockEnrich()`, `bandOf()` | Deterministic offline company data generation via hash |
| Scoring Engine | `score()`, `fitScore()`, `estAnnual()` | Weighted multi-factor scoring (0–100), tier assignment (S/A/B/C) |
| OSINT Processing | `parseOsint()`, `guessPKD()`, `applyOsintOverrides()` | Parse pasted text for domain, employee range, industry keywords |
| UI Rendering | `renderScore()`, `renderActions()`, `renderFirmo()`, `renderOffer()` | DOM updates for all output sections |
| Offer Catalog | `sampleSkus()`, `offerAngle()` | SKU recommendations and sales angles by product category |
| Export | `exportCsv()` | CSV download for CRM import |
| Helpers | `hash()`, `guessName()`, `guessNip()`, `enc()` | Utility functions |

### Scoring Weights
```
employees: 24%, revenueBand: 26%, yearsActive: 10%, vatStatus: 8%,
pkdFit: 16%, basketSignal: 10%, locality: 6%
```

### Tier Thresholds
- **S** (85+): Priority personal contact
- **A** (70–84): Dedicated account manager
- **B** (55–69): Targeted campaigns
- **C** (<55): Occasional follow-up

## Business Domain Context

- **PKD** = Polska Klasyfikacja Działalności (Polish business activity classification)
- **NIP** = 10-digit Polish tax identification number
- **eKRS/CEIDG** = Polish business registries
- **VAT status** checked against "Biała Lista" (White List) by the Ministry of Finance
- Currency is **PLN** (Polish Zloty)
- All UI text is in **Polish**

## Development Workflow

### Frontend
Open `mvp_osint_launcher_szybkie_sprawdzenie_potencjalu_html.html` directly in a browser. No build step, no server needed.

### Backend

```bash
cd backend

# 1. Start PostgreSQL
docker compose up -d

# 2. Create virtualenv and install deps
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env — set CEIDG_API_KEY and GUS_API_KEY if available

# 4. Run migrations
alembic upgrade head

# 5. Start dev server
uvicorn app.main:app --reload --port 8000
```

API docs at `http://localhost:8000/docs` (Swagger UI) or `/redoc`.

### Backend API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/leads` | Create lead |
| GET | `/api/leads` | List leads (filter: `tier`, `city`, `pkd`, `q`) |
| GET | `/api/leads/{id}` | Get lead |
| PUT | `/api/leads/{id}` | Update lead |
| DELETE | `/api/leads/{id}` | Delete lead |
| POST | `/api/scoring/calculate` | Stateless scoring (no DB) |
| POST | `/api/scoring/leads/{id}` | Score lead and persist result |
| GET | `/api/scoring/leads/{id}/history` | Scoring history for a lead |
| GET | `/api/osint/vat/{nip}` | VAT White List check |
| GET | `/api/osint/ekrs/{nip}` | eKRS (KRS registry) lookup |
| GET | `/api/osint/ceidg/{nip}` | CEIDG (sole proprietor registry) lookup |
| GET | `/api/osint/gus/{nip}` | GUS REGON lookup |
| POST | `/api/osint/enrich/{lead_id}` | Auto-enrich lead from all OSINT sources |

### Deployment
GitHub Actions (`.github/workflows/main.yml`) deploys via SSH on push to `main`. It uses secrets: `SSH_PRIVATE_KEY`, `SSH_HOST`, `SSH_USER`.

## Conventions

### Frontend Code Style
- **camelCase** for functions and variables
- **UPPER_CASE** for global state (`OSINT_OVERRIDES`, `CONFIG`)
- Single-line `if` statements and compact function bodies
- `$()` as shorthand for `document.querySelector()`
- Template literals for string interpolation
- Arrow functions preferred

### Backend Code Style
- **snake_case** for functions, variables, file names
- **PascalCase** for classes (SQLAlchemy models, Pydantic schemas)
- **UPPER_CASE** for module-level constants
- Async everywhere — all endpoints and DB calls use `async/await`
- Type hints on all function signatures
- Pydantic models for all request/response validation

### Data Flow (Frontend)
```
Input → mockEnrich() → applyOsintOverrides() → score() → render*() → DOM
```

### Data Flow (Backend)
```
Request → Router → Service → DB/OSINT API → Response
```
- Routers handle HTTP concerns only (validation, status codes)
- Services contain business logic (scoring engine, OSINT fetching)
- Models define the DB schema; schemas define the API contract

### When Modifying the Scoring Engine
- All weights are in `CONFIG.weights` and must sum to 1.0
- Scale arrays (`employeesScale`, `revenueBands`, `yearsScale`) must be sorted ascending by `max`
- Tier thresholds are hardcoded in the `score()` function (lines 243)
- The `CONFIG` object is editable at runtime via the UI textarea

### When Adding OSINT Sources
- Add new buttons in the HTML OSINT section (lines 72–79)
- Register click handlers in `attachOsintButtons()` (lines 265–276)
- URL pattern: Google search with `site:` prefix or keywords appended to the NIP/name

### When Adding Product Categories
- Add the PKD code → category array mapping in `CONFIG.pkdToCategories`
- Add sample SKUs in `sampleSkus()` dictionary
- Add sales angle in `offerAngle()`

## Important Notes

- **No tests exist yet.** Frontend changes should be manually verified in-browser. Backend can be tested via Swagger UI at `/docs`.
- The frontend `hash()` function provides deterministic mock data — same input always produces same output. Do not introduce `Math.random()` into enrichment logic.
- `innerHTML` is used for frontend rendering. Ensure any user-provided data is properly escaped to prevent XSS if the application is ever served from a web server.
- The patch files (`2`, `scripts`, `README.md`) contain improvements that may not yet be applied to the main HTML file.
- **Backend `.env` contains secrets** — never commit it. Use `.env.example` as a template.
- OSINT proxy endpoints call external APIs — CEIDG and GUS require API keys. VAT White List and eKRS are free.
- The scoring engine is duplicated (JS frontend + Python backend). When modifying scoring logic, **update both** to keep results consistent.
- Backend auto-creates tables on startup via `Base.metadata.create_all`. For production, use `alembic upgrade head` instead.
