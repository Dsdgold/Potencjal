# CLAUDE.md

## Project Overview

**Potencjal** is an offline, single-file HTML tool for B2B sales lead assessment in the Polish construction materials sector. It scores client potential using heuristics and manually pasted OSINT data — no APIs, no scraping, no external dependencies.

The entire application lives in one file: `mvp_osint_launcher_szybkie_sprawdzenie_potencjalu_html.html`.

## Repository Structure

```
.
├── mvp_osint_launcher_szybkie_sprawdzenie_potencjalu_html.html  # The application (HTML + CSS + JS)
├── README.md                        # Polish-language usage docs (stored as git patch)
├── scripts                          # Git patch containing setup_github_remote.sh
├── 2                                # Git patch with enrichment/OSINT improvements
├── .github/workflows/main.yml       # GitHub Actions SSH deployment
└── CLAUDE.md                        # This file
```

**Note:** `README.md`, `scripts`, and `2` are stored as git-apply patch files, not standard files. The actual application logic is entirely in the HTML file.

## Technology Stack

- **HTML5** with semantic structure, Polish language (`lang="pl"`)
- **CSS3** — CSS variables for dark theme, Grid/Flexbox layout, responsive (`@media` at 900px)
- **Vanilla JavaScript** (ES2020+) — no frameworks, no libraries, no CDN dependencies
- Zero external dependencies. Runs fully offline in any modern browser.

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

### Running the Application
Open `mvp_osint_launcher_szybkie_sprawdzenie_potencjalu_html.html` directly in a browser. No build step, no server needed.

### Making Changes
1. Edit the single HTML file directly
2. Test by opening/refreshing in a browser
3. There is no build system, linter, test suite, or formatter configured

### Deployment
GitHub Actions (`.github/workflows/main.yml`) deploys via SSH on push to `main`. It uses secrets: `SSH_PRIVATE_KEY`, `SSH_HOST`, `SSH_USER`.

## Conventions

### Code Style
- **camelCase** for functions and variables
- **UPPER_CASE** for global state (`OSINT_OVERRIDES`, `CONFIG`)
- Single-line `if` statements and compact function bodies
- `$()` as shorthand for `document.querySelector()`
- Template literals for string interpolation
- Arrow functions preferred

### Data Flow
```
Input → mockEnrich() → applyOsintOverrides() → score() → render*() → DOM
```
One-way flow: user input produces an enriched entity, which is scored, then rendered. `OSINT_OVERRIDES` is the only global mutable state (besides `CONFIG`).

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

- **No tests exist.** Changes should be manually verified in-browser.
- **No `.gitignore` exists.** Be careful not to commit sensitive or generated files.
- The `hash()` function provides deterministic mock data — same input always produces same output. Do not introduce `Math.random()` into enrichment logic.
- `innerHTML` is used for rendering. Ensure any user-provided data is properly escaped to prevent XSS if the application is ever served from a web server.
- The patch files (`2`, `scripts`, `README.md`) contain improvements that may not yet be applied to the main HTML file.
