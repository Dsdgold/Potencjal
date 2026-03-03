# CLAUDE.md

## Project Overview

**Potencjal** is a B2B sales lead assessment platform for the Polish construction materials sector. It scores client potential using weighted heuristics and OSINT data from Polish public registries. The platform includes user authentication, role-based access control, tiered subscription packages, and both online/offline operating modes.

Two components:
- **Frontend** — single-file SPA (`mvp_osint_launcher_szybkie_sprawdzenie_potencjalu_html.html`, 1134 lines) with offline scoring, auth UI, admin panel, and full dashboard
- **Backend** — Python/FastAPI async API with PostgreSQL, JWT auth, CRUD, scoring engine, OSINT proxy, user management, and package-based feature gating

**Production server:** `46.225.131.52:8000` (Hetzner). Backend serves the frontend HTML at `/`.

## Repository Structure

```
.
├── mvp_osint_launcher_szybkie_sprawdzenie_potencjalu_html.html  # Frontend SPA (HTML + CSS + JS)
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI entry, lifespan (table creation + seed users)
│   │   ├── config.py            # Settings (env vars), PACKAGE_LIMITS
│   │   ├── database.py          # SQLAlchemy async engine + session factory
│   │   ├── dependencies.py      # Auth deps: get_current_user, require_role, require_package_feature
│   │   ├── models.py            # User, Lead, ScoringHistory (SQLAlchemy 2.0)
│   │   ├── schemas.py           # All Pydantic v2 schemas (Lead, Scoring, OSINT, Auth)
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py          # /api/auth — register, login, refresh, me, packages, admin/users
│   │   │   ├── leads.py         # /api/leads — CRUD with ownership + package limits
│   │   │   ├── scoring.py       # /api/scoring — stateless calc + persisted scoring
│   │   │   └── osint.py         # /api/osint — VAT, eKRS, CEIDG, GUS, enrich
│   │   └── services/
│   │       ├── __init__.py
│   │       ├── auth.py          # Password hashing (bcrypt), JWT create/decode
│   │       ├── scoring.py       # Scoring engine (Python port of JS logic)
│   │       └── osint.py         # OSINT proxy to Polish registries (httpx)
│   ├── alembic/
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/
│   │       ├── 001_initial_tables.py    # leads + scoring_history tables
│   │       └── 002_users_and_auth.py    # users table + leads.owner_id FK
│   ├── alembic.ini
│   ├── docker-compose.yml       # PostgreSQL 16 (Alpine)
│   ├── requirements.txt
│   ├── .env.example
│   └── .gitignore
├── deploy.sh                    # Cron-based auto-deploy script (for server)
├── .github/workflows/main.yml   # GitHub Actions: deploy on push to main or claude/**
├── README.md                    # Git patch file
├── scripts                      # Git patch file
├── 2                            # Git patch file
└── CLAUDE.md                    # This file
```

**Note:** `README.md`, `scripts`, and `2` are stored as git-apply patch files, not standard files.

## Technology Stack

### Frontend
- **HTML5** single-file SPA, Polish language (`lang="pl"`)
- **CSS3** — CSS custom properties for dark/light themes, Grid/Flexbox, responsive at 900px and 600px breakpoints
- **Vanilla JavaScript** (ES2020+) — zero frameworks, zero libraries, zero CDN dependencies
- Runs fully offline in any modern browser (localStorage for data persistence)

### Backend
- **Python 3.11+** with **FastAPI 0.115** (async)
- **PostgreSQL 16** via **SQLAlchemy 2.0** (async with asyncpg)
- **Alembic 1.14** for database migrations
- **httpx 0.28** for async HTTP calls to OSINT APIs
- **Pydantic v2** + **pydantic-settings** for validation and config
- **PyJWT 2.9** for JWT token handling
- **passlib + bcrypt** for password hashing
- **Docker Compose** for local PostgreSQL

### Key Dependencies (requirements.txt)
```
fastapi==0.115.6, uvicorn==0.34.0, sqlalchemy==2.0.36, asyncpg==0.30.0,
alembic==1.14.1, pydantic==2.10.4, pydantic-settings==2.7.1, httpx==0.28.1,
python-dotenv==1.0.1, PyJWT==2.9.0, passlib[bcrypt]==1.7.4, bcrypt==4.2.1
```

## Database Models

### User (`users` table)
| Column | Type | Notes |
|--------|------|-------|
| id | UUID (PK) | Auto-generated |
| email | String(255) | Unique, indexed |
| password_hash | String(255) | bcrypt |
| full_name | String(300) | |
| role | String(20) | `admin`, `manager`, `user` (default: `user`) |
| package | String(20) | `starter`, `business`, `pro`, `enterprise` (default: `starter`) |
| is_active | Boolean | Default: true |
| leads_count | Integer | Denormalized counter |
| created_at | DateTime(tz) | Auto |
| last_login | DateTime(tz) | Nullable |

### Lead (`leads` table)
| Column | Type | Notes |
|--------|------|-------|
| id | UUID (PK) | Auto-generated |
| owner_id | UUID (FK → users) | Nullable, ON DELETE SET NULL |
| nip | String(10) | Polish tax ID, indexed |
| name | String(300) | Required |
| city | String(100) | |
| employees | Integer | |
| revenue_pln | Float | |
| revenue_band | String(20) | micro/small/medium/large |
| pkd / pkd_desc | String | Polish business classification |
| years_active | Float | |
| vat_status | String(30) | Czynny VAT / Zwolniony / Niepewny |
| website | String(300) | |
| basket_pln | Float | Current order basket value |
| score | Integer | 0–100 |
| tier | String(1) | S/A/B/C |
| annual_potential | Integer | PLN |
| osint_raw | JSONB | Raw responses from OSINT sources |
| sources | JSONB | List of source names |
| notes | Text | |
| created_at / updated_at | DateTime(tz) | Auto |

### ScoringHistory (`scoring_history` table)
Tracks every scoring event per lead: score, tier, annual_potential, weights_snapshot (JSONB), scored_at.

## Authentication & Authorization

### Auth Flow
1. **Register** → `POST /api/auth/register` → creates User (role=`user`, chosen package)
2. **Login** → `POST /api/auth/login` → returns JWT access (30 min) + refresh (7 days) tokens
3. **Token refresh** → `POST /api/auth/refresh` with refresh token
4. **Current user** → `GET /api/auth/me` (requires Bearer token)

JWT payload: `{sub: user_id, role, pkg, type: "access"|"refresh", exp, iat}`

### Roles (3 levels)
| Role | Leads Access | Admin Panel | User Management |
|------|-------------|-------------|-----------------|
| `admin` | All leads (all users) | Yes | Full CRUD on users |
| `manager` | All leads (all users) | No | No |
| `user` | Own leads only | No | No |

### Packages (feature gating)
| Package | Price | Max Leads | OSINT Sources | Bulk | CSV Export |
|---------|-------|-----------|---------------|------|------------|
| `starter` | 0 PLN | 5 | None | No | No |
| `business` | 49 PLN/mo | 100 | VAT + eKRS | No | Yes |
| `pro` | 149 PLN/mo | Unlimited | All 4 sources | Yes | Yes |
| `enterprise` | Contact | Unlimited | All 4 sources | Yes | Yes |

### Seed Users (created on first startup if DB is empty)
| Email | Password | Role | Package |
|-------|----------|------|---------|
| admin@potencjal.pl | admin123 | admin | enterprise |
| jan.kowalski@example.pl | test123 | manager | pro |
| anna.nowak@example.pl | test123 | user | business |
| demo@example.pl | demo123 | user | starter |

Admin email/password configurable via `ADMIN_EMAIL`/`ADMIN_PASSWORD` env vars.

## API Endpoints

### Auth (`/api/auth`)
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/register` | No | Create account |
| POST | `/login` | No | Get JWT tokens |
| POST | `/refresh` | No | Refresh access token |
| GET | `/me` | Yes | Current user info |
| PUT | `/me` | Yes | Update name/password |
| GET | `/packages` | No | List available packages |
| GET | `/admin/users` | Admin | List all users |
| PUT | `/admin/users/{id}` | Admin | Update user role/package/status |
| DELETE | `/admin/users/{id}` | Admin | Delete user |

### Leads (`/api/leads`)
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/` | Yes | Create lead (checks package lead limit) |
| GET | `/` | Yes | List leads (filters: `tier`, `city`, `pkd`, `q`, `offset`, `limit`) |
| GET | `/{id}` | Yes | Get lead (ownership check for `user` role) |
| PUT | `/{id}` | Yes | Update lead |
| DELETE | `/{id}` | Yes | Delete lead |

### Scoring (`/api/scoring`)
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/calculate` | No | Stateless scoring (no DB write) |
| POST | `/leads/{id}` | Yes | Score lead and persist to DB + history |
| GET | `/leads/{id}/history` | Yes | Scoring history for a lead |

### OSINT (`/api/osint`)
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/vat/{nip}` | No | VAT White List check (free, no key) |
| GET | `/ekrs/{nip}` | No | eKRS KRS registry lookup (free, no key) |
| GET | `/ceidg/{nip}` | No | CEIDG lookup (requires `CEIDG_API_KEY`) |
| GET | `/gus/{nip}` | No | GUS REGON SOAP lookup (requires `GUS_API_KEY`) |
| POST | `/enrich/{lead_id}` | Yes | Auto-enrich lead from all OSINT sources |

### Other
| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check → `{"status": "ok"}` |
| GET | `/` | Serves the frontend HTML file |

## Frontend Architecture (Single-File SPA)

### Structure (1134 lines)
- **CSS** (lines 7–168): Dark/light theme via CSS variables, responsive grid, component styles
- **HTML** (lines 170–437): 9 views — dashboard, newlead, detail, config, landing, login, register, profile, admin
- **JavaScript** (lines 439–1132): All application logic

### Views & Navigation
| View ID | Description | Auth Required |
|---------|-------------|---------------|
| `landing` | Public landing page with pricing cards | No |
| `login` | Login form | No |
| `register` | Registration form with package selection | No |
| `dashboard` | KPI row, scoring histogram, leads table with sort/filter/pagination | Yes |
| `newlead` | Lead creation form + OSINT tools + offline scoring | Yes |
| `detail` | Lead firmography, scoring ring, breakdown, actions, offer matching, history, notes | Yes |
| `config` | JSON editor for scoring CONFIG | Yes |
| `profile` | User profile editor (name, password) | Yes |
| `admin` | User management table (admin role only) | Yes (admin) |

### Key JavaScript Modules

| Module | Functions | Purpose |
|--------|----------|---------|
| Token Management | `getToken()`, `setTokens()`, `clearTokens()` | JWT in localStorage (`pot_token`, `pot_refresh`) |
| API Client | `apic(path, opts)` | Fetch wrapper with auth headers, auto-refresh on 401 |
| Auth | `doLogin()`, `doRegister()`, `loadUser()`, `logout()` | Auth flows |
| Offline Scoring | `offScore(d)`, `hash()`, `mockEn()` | Client-side scoring matching backend logic |
| OSINT | `parsePaste()`, `guessPKD()`, `initOsint()` | OSINT paste parsing + Google search launchers |
| Rendering | `ringHTML()`, `breakdownHTML()`, `firmoHTML()`, `offerHTML()` | Score ring SVG, breakdown bars, firmography table |
| Dashboard | `renderKpis()`, `renderChart()`, `renderTable()` | KPI cards, histogram chart, sortable lead table |
| Navigation | `go(view)` | View switching with auth guards |
| Theme | `toggleTheme()` | Dark/light toggle persisted to localStorage |
| Admin | `loadAdmin()`, `adminSetRole()`, `adminSetPkg()`, `adminDel()` | Admin user management |
| Demo Data | `DEMO_LEADS[]`, `seedDemoData()` | 12 pre-built demo leads for offline mode |

### Keyboard Shortcuts
| Key | Action |
|-----|--------|
| N | New lead |
| / or S | Search (focus search box) |
| D | Dashboard |
| K | Config |
| T | Toggle theme |
| ? | Show shortcuts panel |
| Esc | Close modal / go to Dashboard |

### Offline Mode
When the backend is unreachable, the frontend automatically:
- Seeds 12 demo leads into localStorage on first load
- Uses `offScore()` for client-side scoring
- Stores leads in `localStorage` key `pot_leads`
- Hides auth UI (nav, user menu)

### API Connection
```javascript
const API = location.port === '8000'
  ? location.origin
  : (location.hostname === 'localhost' || location.hostname === '127.0.0.1'
    ? 'http://localhost:8000'
    : 'http://46.225.131.52:8000');
```

## Scoring Engine

The scoring engine exists in **two identical implementations** that MUST be kept in sync:
- **Frontend JS:** `offScore()` function (line ~555)
- **Backend Python:** `backend/app/services/scoring.py` → `calculate_score()`

### Weights (must sum to 1.0)
```
employees: 0.24, revenueBand: 0.26, yearsActive: 0.10, vatStatus: 0.08,
pkdFit: 0.16, basketSignal: 0.10, locality: 0.06
```

### Scales
| Factor | Ranges → Score |
|--------|---------------|
| Employees | ≤9→20, ≤49→55, ≤249→78, >249→92 |
| Revenue (PLN) | <2M→25 (micro), <10M→55 (small), <50M→75 (medium), ≥50M→92 (large) |
| Years Active | ≤1→20, ≤3→40, ≤7→60, ≤12→75, >12→88 |
| VAT Status | Czynny VAT→80, Zwolniony→55, else→35 |
| PKD Fit | Base 50 (no PKD) or 70 (has PKD) + size adjustment (>200 emp: +12, >50: +6), cap 92 |
| Basket Signal | `30 + (min(1, basket/8000)^0.65) * 60` |
| Locality | In major city→75, else→55 |

Major cities: Warszawa, Kraków, Wrocław, Poznań, Gdańsk, Katowice, Łódź

### Tier Thresholds
| Tier | Score | Action |
|------|-------|--------|
| **S** | 85+ | Priority personal contact — call today |
| **A** | 70–84 | Volume discount offer with 24–48h delivery |
| **B** | 55–69 | Remarketing campaign, follow-up 7 days |
| **C** | <55 | Monitor, follow-up 30 days |

### Annual Potential Model
`base_arpu (18,000 PLN) × tier_multiplier` → S: ×30 (540k), A: ×12 (216k), B: ×5 (90k), C: ×2 (36k)

## OSINT Sources

| Source | API | Auth | Data Retrieved |
|--------|-----|------|---------------|
| VAT White List | `wl-api.mf.gov.pl` | None (free) | VAT status, name, city, REGON, KRS |
| eKRS | `api-krs.ms.gov.pl` | None (free) | Company name, KRS, REGON, PKD, city, registration date |
| CEIDG | `dane.biznes.gov.pl/api/ceidg/v2` | Bearer token (`CEIDG_API_KEY`) | Sole proprietor: name, city, PKD, start date, website |
| GUS REGON | `wyszukiwarkaregon.stat.gov.pl` (SOAP) | Session key (`GUS_API_KEY`) | Name, city, REGON, PKD |

Enrichment merges results using **first-non-null** strategy across all sources.

## Development Workflow

### Frontend
Open `mvp_osint_launcher_szybkie_sprawdzenie_potencjalu_html.html` directly in a browser. No build step required.
When served by the backend, available at `http://localhost:8000/`.

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

API docs: `http://localhost:8000/docs` (Swagger) or `/redoc`.

### Environment Variables (.env)
| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://potencjal:potencjal@localhost:5432/potencjal` | DB connection |
| `CEIDG_API_KEY` | (empty) | CEIDG registry API key |
| `GUS_API_KEY` | (empty) | GUS REGON API key |
| `JWT_SECRET` | `change-me-in-production...` | JWT signing secret |
| `JWT_ACCESS_MINUTES` | 30 | Access token TTL |
| `JWT_REFRESH_DAYS` | 7 | Refresh token TTL |
| `ADMIN_EMAIL` | `admin@potencjal.pl` | Default admin email (seed) |
| `ADMIN_PASSWORD` | `admin123` | Default admin password (seed) |

## Deployment

### GitHub Actions (`.github/workflows/main.yml`)
- Triggers on push to `main` or `claude/**` branches
- Steps: checkout → SSH key setup → rsync frontend to `/var/www/html/` → rsync backend to `/opt/potencjal/backend/` (excludes `.env`, `.venv`, `__pycache__`) → remote: docker compose up, pip install, alembic upgrade, restart uvicorn → health check
- Secrets: `SSH_PRIVATE_KEY` (base64-encoded ed25519), `SSH_HOST`, `SSH_USER`

### Cron Deploy Script (`deploy.sh`)
Alternative cron-based deploy (every 2 min) that clones repo, compares hash, rsync + restart on change. For use directly on the server.

### Server Layout
```
/opt/potencjal/backend/   # Backend code + .venv + .env
/var/www/html/            # Frontend HTML file
```

## Code Conventions

### Frontend (JavaScript)
- **camelCase** for functions and variables (`offScore`, `curLead`, `apiOn`)
- **UPPER_CASE** for constants and global config (`CONFIG`, `DCFG`, `SKU`, `PKD`, `API`)
- Compact single-line expressions, minimal whitespace
- `esc()` for XSS-safe HTML escaping (creates text node)
- `apic()` for all authenticated API calls
- `toast(type, msg)` for user notifications (`'ok'`, `'err'`, `'info'`)
- `go(viewName)` for navigation
- All state in globals: `leads`, `curLead`, `curUser`, `pg`, `sortCol`, `sortDir`, `kpiFilter`

### Backend (Python)
- **snake_case** for functions, variables, file names
- **PascalCase** for classes (SQLAlchemy models, Pydantic schemas)
- **UPPER_CASE** for module-level constants
- Async everywhere — all endpoints and DB calls use `async/await`
- Type hints with `Mapped[]` for SQLAlchemy 2.0 mapped columns
- Union types with `X | None` syntax (Python 3.10+)
- Pydantic v2 `model_config = {"from_attributes": True}` for ORM mode

### Data Flow (Frontend — Online)
```
Login → JWT → apic() → /api/leads → leads[] → renderTable() → DOM
                     → /api/scoring/leads/{id} → renderDet() → DOM
                     → /api/osint/enrich/{id} → fillForm() → DOM
```

### Data Flow (Frontend — Offline)
```
Input → mockEn() → offScore() → ringHTML() + breakdownHTML() → DOM
localStorage('pot_leads') ↔ leads[]
```

### Data Flow (Backend)
```
Request → Router → Service → DB/OSINT API → Response
```
- Routers: HTTP concerns (validation, status codes, auth deps)
- Services: Business logic (scoring, OSINT fetching, password hashing)
- Models: DB schema; Schemas: API contract

## Important Rules

### When Modifying the Scoring Engine
- **Update BOTH** frontend JS (`offScore()`) and backend Python (`calculate_score()`) — they must produce identical results
- All weights in `CONFIG.weights` / `DEFAULT_WEIGHTS` must sum to **1.0**
- Scale arrays must be sorted ascending by `max`
- Tier thresholds: S≥85, A≥70, B≥55, C<55

### When Modifying Authentication
- JWT tokens contain `sub` (user ID), `role`, `pkg` (package), `type` (access/refresh)
- `dependencies.py` provides `get_current_user`, `get_optional_user`, `require_role(*roles)`, `require_package_feature(feature)`
- Lead ownership enforced in router: `user` role sees only own leads; `admin`/`manager` see all
- Package limits checked on lead creation (max_leads per package)

### When Adding OSINT Sources
- Backend: add `fetch_*()` function in `backend/app/services/osint.py`, add to `enrich_lead()` loop
- Backend: add route in `backend/app/routers/osint.py`
- Frontend: add button in `initOsint()` function (line ~990)

### When Adding Product Categories
- Add PKD → categories mapping in both `CONFIG.pkdToCategories` (JS) and `PKD_TO_CATEGORIES` (Python)
- Add SKU list in `SKU` object (JS) and `sampleSkus()` equivalent
- Add sales angle in `offerAngle()` (JS) / `_recommended_actions()` (Python)

### When Modifying the Frontend HTML
- The file is a single self-contained HTML document — CSS, HTML, and JS are all inline
- All views are `<div class="view">` elements toggled by `go()` function
- Theme variables defined in `:root` (dark) and `html.light` (light mode)
- Responsive breakpoints: 900px (tablet), 600px (mobile)
- User data escaped via `esc()` before `innerHTML` insertion to prevent XSS

## Security Notes

- **No tests exist yet.** Verify changes manually via browser and Swagger UI.
- **`.env` contains secrets** — never commit. Use `.env.example` as template.
- CORS is set to `allow_origins=["*"]` — restrict in production.
- Default admin password is `admin123` — change via env var in production.
- `innerHTML` used for rendering — all user input must go through `esc()`.
- NIP validation uses Polish checksum algorithm (weighted digit sum mod 11).
- The `hash()` function provides deterministic mock data — do not introduce `Math.random()`.

## Evolution Roadmap: BuildLeads SaaS

The project is evolving from a single-tenant MVP ("Potencjal") into a multi-tenant SaaS platform ("BuildLeads"). The planned architecture includes:

### Planned Components (Not Yet Implemented)
- **Multi-tenancy** with tenant isolation (tenant_id on all tables)
- **Next.js 14+** frontend (TypeScript, Tailwind, shadcn/ui) replacing the single HTML file
- **Celery + Redis** for background jobs (scraping, scoring, email dispatch)
- **Ollama / Llama 3.2 3B** for AI-powered lead qualification
- **Stripe billing** with subscription plans (trial, starter, growth, enterprise)
- **Automated data collectors**: BZP (public procurement), GUNB (building permits), TED (EU tenders), KRS (new companies)
- **Email dispatch**: Resend API for morning lead digests, weekly summaries, alerts
- **4 roles**: Platform Admin, Manager, Salesperson, Viewer
- **Regions**: Geographic assignment of users and leads by voivodeship
- **Leaflet map**: Poland map with lead markers
- **Docker Compose** full stack: API, worker, beat, frontend, db, redis, ollama, nginx

### Target Tech Stack
Backend: Python 3.12+, FastAPI, SQLAlchemy 2.0, Alembic, Celery, Redis, Stripe SDK, Resend, Ollama, Playwright
Frontend: Next.js 14+, TypeScript (strict), Tailwind CSS, shadcn/ui, Leaflet, TanStack Table/Query, Recharts, Zod
Infra: Docker Compose, Nginx, Let's Encrypt, Hetzner Dedicated (8 vCPU, 16 GB RAM)

### Phase Plan
1. Auth + Users + Tenants + Regions (core multi-tenancy)
2. Leads model + BZP collector + basic dashboard
3. AI qualification pipeline (Ollama)
4. Email system + morning digest
5. Stripe billing + plans
6. Admin panel + additional collectors (GUNB, KRS, TED)
7. Map + advanced dashboard + notifications
