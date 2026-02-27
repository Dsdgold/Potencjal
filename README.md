# SIG Potencjał — Company Intelligence & Credit Risk Platform

Production-ready SaaS for Polish/EU company intelligence, credit risk scoring,
and construction material recommendations.

## Quick Start

```bash
# 1. Copy env file
cp .env.example .env

# 2. Start all services
docker-compose up --build

# 3. Access
#    - Frontend: http://localhost:3000 (Next.js)
#    - API docs: http://localhost:8000/docs
#    - Static landing: index.html (simple deploy)
```

**Demo credentials**: `demo@sig.pl` / `demo1234` or `admin@sig.pl` / `admin1234`

## Architecture

```
┌──────────┐  ┌──────────┐  ┌──────────┐
│  Next.js │  │  FastAPI  │  │  Celery  │
│  :3000   │──│  :8000   │──│  Worker  │
└──────────┘  └────┬─────┘  └────┬─────┘
                   │              │
         ┌─────────┼──────────────┤
         │         │              │
    ┌────▼───┐ ┌───▼────┐  ┌─────▼───┐
    │Postgres│ │ Redis  │  │ Qdrant  │
    │  :5432 │ │ :6379  │  │ :6333   │
    └────────┘ └────────┘  └─────────┘
```

## Data Providers

| Provider | Auth | Status |
|----------|------|--------|
| Biała Lista VAT (MF) | None (public) | Implemented |
| KRS OpenAPI (MS) | None (public) | Implemented |
| GUS REGON (BIR1) | API key required | Implemented (needs key) |
| CEIDG | API key required | Implemented (needs key) |
| Mock Provider | None | For dev/testing |

### Adding Provider Keys

1. **GUS REGON**: Get key at https://api.stat.gov.pl — set `GUS_API_KEY` in `.env`
2. **CEIDG**: Get key at https://dane.biznes.gov.pl — set `CEIDG_API_KEY` in `.env`
3. **Stripe**: Create account at stripe.com — set `STRIPE_*` keys in `.env`

## Scoring Engine (11 components, 0-100)

| Component | Max | Source |
|-----------|-----|--------|
| Status VAT | 12 | Biala Lista |
| Forma prawna | 12 | VAT / KRS |
| Wiek firmy | 10 | VAT / KRS |
| Lokalizacja | 8 | VAT / KRS |
| Rachunki bankowe | 8 | Biala Lista |
| Rejestry publiczne | 10 | All |
| Zarzad | 8 | VAT / KRS |
| Kapital zakladowy | 10 | KRS |
| Branza PKD | 7 | KRS / CEIDG |
| Kompletnosc danych | 8 | All |
| Stabilnosc | 7 | All |

Risk bands: **A** (75+), **B** (55+), **C** (35+), **D** (<35)

## Credit Limits

| Band | Limit | Terms | Discount |
|------|-------|-------|----------|
| A | 200K-1M PLN | 60 days | 15% |
| B | 50K-400K PLN | 45 days | 10% |
| C | 10K-100K PLN | 30 days | 5% |
| D | Prepayment | n/a | n/a |

## Material Categories (15)

Cement, insulation, drywall, rebar, aggregates, roofing, facade,
windows/doors, waterproofing, adhesives, paints, pipes, electrical, HVAC, tools.

## Plans

- **Free**: 10 lookups/month, scoring, credit limit, 1 user
- **Pro** (299 PLN/mo): 200 lookups, materials, export, CRM, 5 users
- **Enterprise** (999 PLN/mo): 5000 lookups, API, SSO, unlimited users

## Testing

```bash
python -m pytest tests/api/ -v   # 17 tests
```

## Key Assumptions

- In development mode, the mock provider is used automatically
- VAT Whitelist API is public, rate-limited (~10 req/s)
- KRS requires a KRS number (obtained from VAT lookup first)
- GUS and CEIDG require API keys from government portals
- Stripe is optional; billing degrades gracefully without keys
- GDPR: snapshots auto-expire per TTL; audit logs are append-only
