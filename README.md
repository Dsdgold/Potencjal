# Potencjał klienta – narzędzie offline

Ten repozytorium zawiera pojedynczy plik HTML implementujący narzędzie do szybkiej oceny potencjału klienta z wykorzystaniem heurystyk oraz ręcznie wklejanych danych OSINT.

## Uruchomienie

1. Otwórz plik `mvp_osint_launcher_szybkie_sprawdzenie_potencjalu_html.html` w przeglądarce (dwuklik lub `open` / `xdg-open`).
2. Wpisz nazwę firmy lub NIP, opcjonalnie miasto i wartość aktualnego koszyka.
3. Skorzystaj z przycisków wyszukiwania, aby otworzyć dodatkowe karty OSINT.
4. Wklej znalezione dane w sekcję „Wklej dane znalezione w sieci" i kliknij „Zastosuj wklejkę do profilu", aby natychmiast przeliczyć scoring.

## BuildLeads SaaS

Nowa wersja platformy w katalogu `buildleads/`:

```bash
cd buildleads

# Uruchom bazę danych i Redis
docker compose up -d db redis

# Backend (port 8001)
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn src.main:app --reload --port 8001

# Frontend (port 3000) — w osobnym terminalu
cd ../frontend
npm install
npm run dev
```

- Frontend: http://localhost:3000
- Backend API: http://localhost:8001
- Swagger docs: http://localhost:8001/docs
- Login: `admin@buildleads.pl` / `admin123`
