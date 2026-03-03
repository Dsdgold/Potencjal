"""OSINT proxy — fetches maximum data from Polish public registries.

Sources:
  - VAT White List (free) — name, address, VAT status, REGON, KRS, bank accounts, representatives
  - eKRS (free) — full KRS extract: board, shareholders, capital, PKD codes, registration date
  - GUS BIR1.1 (test key works!) — PKD, REGON, KRS, legal form, founding date, address
  - CEIDG (requires API key) — sole proprietor data

Enrichment chain: VAT → GUS (get PKD + KRS) → eKRS (by KRS from VAT/GUS) → CEIDG.
"""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime
from dataclasses import dataclass, field

import httpx

from src.config import settings

logger = logging.getLogger(__name__)
TIMEOUT = httpx.Timeout(15.0, connect=5.0)

# GUS BIR1.1 test key — works on test environment with REAL data
GUS_TEST_KEY = "abcde12345abcde12345"
GUS_PROD_URL = "https://wyszukiwarkaregon.stat.gov.pl/wsBIR/UslugaBIRzewn662.svc"
GUS_TEST_URL = "https://wyszukiwarkaregontest.stat.gov.pl/wsBIR/UslugaBIRzewn662.svc"


@dataclass
class OsintResult:
    source: str
    nip: str | None = None
    name: str | None = None
    city: str | None = None
    employees: int | None = None
    revenue_pln: float | None = None
    pkd: str | None = None
    pkd_desc: str | None = None
    years_active: float | None = None
    vat_status: str | None = None
    website: str | None = None
    regon: str | None = None
    krs: str | None = None
    raw: dict | None = None


# ── VAT White List ────────────────────────────────────────────────────

async def fetch_vat_whitelist(nip: str) -> OsintResult:
    url = f"https://wl-api.mf.gov.pl/api/search/nip/{nip}"
    today = datetime.now().strftime("%Y-%m-%d")
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(url, params={"date": today})
        resp.raise_for_status()
        data = resp.json()

    subject = (data.get("result") or {}).get("subject") or {}
    status = subject.get("statusVat", "")
    vat_status = _map_vat_status(status)
    name = subject.get("name", "")
    city = _extract_city(subject.get("residenceAddress") or subject.get("workingAddress") or "")
    regon = subject.get("regon", "")
    krs = subject.get("krs", "")

    years_active = None
    reg_date_str = subject.get("registrationLegalDate")
    if reg_date_str:
        try:
            reg_date = datetime.strptime(str(reg_date_str)[:10], "%Y-%m-%d")
            years_active = round((datetime.now() - reg_date).days / 365.25, 1)
        except ValueError:
            pass

    return OsintResult(
        source="vat_whitelist", nip=nip, name=name or None, city=city or None,
        vat_status=vat_status, regon=regon or None, krs=krs or None,
        years_active=years_active, raw=data,
    )


def _map_vat_status(status: str) -> str:
    s = status.lower()
    if "czynny" in s:
        return "Czynny VAT"
    if "zwolniony" in s:
        return "Zwolniony"
    return "Niepewny"


def _extract_city(address: str) -> str:
    parts = [p.strip() for p in address.split(",")]
    for part in reversed(parts):
        cleaned = re.sub(r"\d{2}-\d{3}", "", part).strip()
        if cleaned and not any(ch.isdigit() for ch in cleaned):
            return cleaned
    return ""


# ── GUS BIR1.1 ───────────────────────────────────────────────────────

async def fetch_gus(nip: str) -> OsintResult:
    """GUS REGON — tries production URL first (with prod key or test key),
    then falls back to test environment. The test env may not have real companies."""

    # Try configurations in order: production key → test key on prod → test env
    configs = []
    if settings.gus_api_key:
        configs.append((settings.gus_api_key, GUS_PROD_URL))
    configs.append((GUS_TEST_KEY, GUS_PROD_URL))
    configs.append((GUS_TEST_KEY, GUS_TEST_URL))

    for api_key, wsdl_url in configs:
        try:
            result = await _fetch_gus_with_config(nip, api_key, wsdl_url)
            if result.name or result.regon or result.pkd:
                return result
        except Exception as exc:
            logger.debug("GUS attempt %s failed: %s", wsdl_url, exc)
            continue

    return OsintResult(source="gus", nip=nip, raw={"error": "all_gus_attempts_failed"})


async def _fetch_gus_with_config(nip: str, api_key: str, wsdl_url: str) -> OsintResult:
    """GUS REGON lookup with a specific key/URL pair."""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        # Step 1: Login
        login_body = _gus_soap(wsdl_url, "Zaloguj",
            f"<ns:Zaloguj><ns:pKluczUzytkownika>{api_key}</ns:pKluczUzytkownika></ns:Zaloguj>")
        login_resp = await client.post(wsdl_url, content=login_body,
            headers={"Content-Type": "application/soap+xml; charset=utf-8"})
        login_resp.raise_for_status()
        sid_match = re.search(r"<ZalogujResult>(.*?)</ZalogujResult>", login_resp.text)
        if not sid_match or not sid_match.group(1):
            return OsintResult(source="gus", nip=nip, raw={"error": "login_failed"})
        sid = sid_match.group(1)
        headers = {"Content-Type": "application/soap+xml; charset=utf-8", "sid": sid}

        # Step 2: Search by NIP
        search_body = _gus_soap(wsdl_url, "DaneSzukajPodmioty",
            '<ns:DaneSzukajPodmioty><ns:pParametryWyszukiwania>'
            f'<dat:Nip>{nip}</dat:Nip>'
            '</ns:pParametryWyszukiwania></ns:DaneSzukajPodmioty>')
        search_resp = await client.post(wsdl_url, content=search_body, headers=headers)
        search_resp.raise_for_status()

        # Parse basic search results
        name = _xml_value(search_resp.text, "Nazwa")
        city = _xml_value(search_resp.text, "Miejscowosc")
        regon = _xml_value(search_resp.text, "Regon")
        voivodeship = _xml_value(search_resp.text, "Wojewodztwo")
        street = _xml_value(search_resp.text, "Ulica")
        building = _xml_value(search_resp.text, "NrNieruchomosci")
        postal = _xml_value(search_resp.text, "KodPocztowy")
        typ = _xml_value(search_resp.text, "Typ")  # P = legal entity, F = sole proprietor

        # Step 3: Full report for PKD, KRS, legal form, founding date
        pkd = None
        pkd_desc = None
        krs = None
        legal_form = None
        years_active = None
        report_data: dict = {}

        if regon:
            report_name = "BIR11OsPrawna" if typ == "P" else "BIR11OsFizycznaDzworki"
            report_body = _gus_soap(wsdl_url, "DanePobierzPelnyRaport",
                '<ns:DanePobierzPelnyRaport>'
                f'<ns:pRegon>{regon}</ns:pRegon>'
                f'<ns:pNazwaRaportu>{report_name}</ns:pNazwaRaportu>'
                '</ns:DanePobierzPelnyRaport>')
            try:
                report_resp = await client.post(wsdl_url, content=report_body, headers=headers)
                report_resp.raise_for_status()
                rt = report_resp.text

                if typ == "P":
                    pkd = _xml_value(rt, "praw_pkdKod")
                    pkd_desc = _xml_value(rt, "praw_pkdNazwa")
                    krs = _xml_value(rt, "praw_numerWRejestrzeEwidencji")
                    legal_form = _xml_value(rt, "praw_podstawowaFormaPrawnaNazwa")
                    founding = _xml_value(rt, "praw_dataPowstania")
                    if founding:
                        try:
                            fd = datetime.strptime(founding[:10], "%Y-%m-%d")
                            years_active = round((datetime.now() - fd).days / 365.25, 1)
                        except ValueError:
                            pass
                else:
                    pkd = _xml_value(rt, "fiz_pkdKod")
                    pkd_desc = _xml_value(rt, "fiz_pkdNazwa")
                    founding = _xml_value(rt, "fiz_dataRozpoczeciaDzialalnosci")
                    if founding:
                        try:
                            fd = datetime.strptime(founding[:10], "%Y-%m-%d")
                            years_active = round((datetime.now() - fd).days / 365.25, 1)
                        except ValueError:
                            pass

                report_data["report_snippet"] = rt[:3000]
            except Exception as exc:
                logger.warning("GUS full report failed for REGON %s: %s", regon, exc)

    return OsintResult(
        source="gus", nip=nip, name=name or None, city=city or None,
        regon=regon or None, krs=krs or None, pkd=pkd or None, pkd_desc=pkd_desc or None,
        years_active=years_active,
        raw={
            "search_snippet": search_resp.text[:2000],
            "_parsed": {
                "voivodeship": voivodeship or None,
                "street": street or None,
                "building": building or None,
                "postal_code": postal or None,
                "entity_type": typ or None,
                "legal_form": legal_form or None,
                "pkd": pkd or None,
                "pkd_desc": pkd_desc or None,
                "krs": krs or None,
                "founding_date": _xml_value(report_data.get("report_snippet", ""), "praw_dataPowstania") if report_data else None,
            },
            **report_data,
        },
    )


def _gus_soap(url: str, action: str, body: str) -> str:
    return f"""<?xml version="1.0" encoding="utf-8"?>
    <soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope"
                   xmlns:ns="http://CIS/BIR/PUBL/2014/07"
                   xmlns:dat="http://CIS/BIR/PUBL/2014/07/DataContract">
      <soap:Header xmlns:wsa="http://www.w3.org/2005/08/addressing">
        <wsa:Action>http://CIS/BIR/PUBL/2014/07/IUslugaBIR/{action}</wsa:Action>
        <wsa:To>{url}</wsa:To>
      </soap:Header>
      <soap:Body>{body}</soap:Body>
    </soap:Envelope>"""


# ── eKRS ──────────────────────────────────────────────────────────────

async def fetch_ekrs(nip: str, krs_number: str | None = None) -> OsintResult:
    """eKRS — tries KRS number first (from VAT/GUS), then NIP as fallback.

    Parses the real api-krs.ms.gov.pl format (key=``odpis``, array-based
    fields, PKD in dzial3, shareholders/capital in dzial1).
    """
    identifiers = []
    if krs_number and krs_number.strip():
        identifiers.append(krs_number.strip().zfill(10))
    identifiers.append(nip)

    data = None
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        for identifier in identifiers:
            url = f"https://api-krs.ms.gov.pl/api/krs/OdpisPelny/{identifier}"
            try:
                resp = await client.get(url, params={"rejestr": "P", "format": "json"})
                if resp.status_code == 200:
                    payload = resp.json()
                    if payload.get("odpis") or payload.get("odppisPelnyJSON"):
                        data = payload
                        break
            except Exception as exc:
                logger.warning("eKRS lookup %s failed: %s", identifier, exc)

    if not data:
        return OsintResult(source="ekrs", nip=nip, raw={"error": "not_found"})

    # Support both old (odppisPelnyJSON) and new (odpis) API formats
    root = data.get("odpis") or data.get("odppisPelnyJSON") or {}
    dane = root.get("dane", {})
    naglowek = root.get("naglowekP", {})
    dzial1 = dane.get("dzial1", {})
    dzial2 = dane.get("dzial2", {})
    dzial3 = dane.get("dzial3", {})

    # --- Name, identifiers, legal form from danePodmiotu ---
    dp = dzial1.get("danePodmiotu", {})
    name = _ekrs_last(dp.get("nazwa", []), "nazwa")
    legal_form = _ekrs_last(dp.get("formaPrawna", []), "formaPrawna")

    # Identifiers (REGON, NIP) — take the latest entry
    ids_list = dp.get("identyfikatory", [])
    regon = ""
    nip_from_krs = ""
    for entry in reversed(ids_list):
        ids_inner = entry.get("identyfikatory", {})
        if not regon and ids_inner.get("regon"):
            regon = ids_inner["regon"]
        if not nip_from_krs and ids_inner.get("nip"):
            nip_from_krs = ids_inner["nip"]

    krs = naglowek.get("numerKRS", "")

    # --- Address ---
    sia = dzial1.get("siedzibaIAdres", {})
    addr_list = sia.get("adres", [])
    addr = addr_list[-1] if addr_list else {}  # latest address
    city = addr.get("miejscowosc", "")
    voivodeship = ""
    siedz_list = sia.get("siedziba", [])
    if siedz_list:
        voivodeship = siedz_list[-1].get("wojewodztwo", "")

    # --- PKD from dzial3 ---
    pkd_section = dzial3.get("przedmiotDzialalnosci", {})
    pkd_main_raw = pkd_section.get("przedmiotPrzewazajacejDzialalnosci", [])
    pkd_rest_raw = pkd_section.get("przedmiotPozostalejDzialalnosci", [])

    def _parse_pkd_entries(entries: list) -> list[dict]:
        result = []
        for entry in entries:
            for poz in entry.get("pozycja", []):
                code = f"{poz.get('kodDzial', '')}.{poz.get('kodKlasa', '')}.{poz.get('kodPodklasa', '')}".strip(".")
                desc = poz.get("opis", "")
                if code:
                    result.append({"code": code, "desc": desc})
        return result

    pkd_main_list = _parse_pkd_entries(pkd_main_raw)
    pkd_rest_list = _parse_pkd_entries(pkd_rest_raw)
    pkd_code = pkd_main_list[0]["code"] if pkd_main_list else ""
    pkd_desc = pkd_main_list[0]["desc"] if pkd_main_list else ""

    # --- Registration date from naglowek ---
    reg_date_str = None
    years_active = None
    wpisy = naglowek.get("wpis", [])
    if wpisy:
        first_wpis = wpisy[0].get("dataWpisu", "")
        if first_wpis:
            reg_date_str = first_wpis
            try:
                for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
                    try:
                        reg_date = datetime.strptime(first_wpis, fmt)
                        years_active = round((datetime.now() - reg_date).days / 365.25, 1)
                        break
                    except ValueError:
                        continue
            except Exception:
                pass

    # --- Board of Directors from dzial2.reprezentacja ---
    board_members = []
    organ_name = "Zarząd"
    repr_list = dzial2.get("reprezentacja", [])
    if isinstance(repr_list, list):
        for organ in repr_list:
            names_list = organ.get("nazwaOrganu", [])
            if names_list:
                organ_name = _ekrs_last(names_list, "nazwaOrganu") or organ_name
            for member in organ.get("sklad", []):
                board_members.append(_ekrs_person(member))

    # --- Supervisory Board from dzial2.organNadzoru ---
    supervisory = []
    nadzor_list = dzial2.get("organNadzoru", [])
    if isinstance(nadzor_list, list):
        for organ in nadzor_list:
            for member in organ.get("sklad", []):
                supervisory.append(_ekrs_person(member))

    # --- Capital from dzial1.kapital ---
    capital_section = dzial1.get("kapital", {})
    capital_entries = capital_section.get("wysokoscKapitaluZakladowego", [])
    capital = None
    if capital_entries:
        latest = capital_entries[-1]
        capital = f"{latest.get('wartosc', '')} {latest.get('waluta', '')}".strip()

    # --- Shareholders from dzial1.wspolnicySpzoo ---
    shareholders = []
    wspolnicy_list = dzial1.get("wspolnicySpzoo", []) or []
    for w in wspolnicy_list:
        person = _ekrs_person(w)
        shares = ""
        udzialy = w.get("posiadaneUdzialy", [])
        if isinstance(udzialy, list) and udzialy:
            u = udzialy[-1]
            if isinstance(u, dict):
                shares = u.get("posiadaneUdzialy", str(u))
            else:
                shares = str(u)
        elif isinstance(udzialy, str):
            shares = udzialy
        shareholders.append({"name": person["name"], "shares": shares})

    enriched_raw = dict(data)
    enriched_raw["_parsed"] = {
        "legal_form": legal_form,
        "voivodeship": voivodeship,
        "full_address": addr,
        "pkd_main": {"code": pkd_code, "desc": pkd_desc} if pkd_code else None,
        "pkd_all": pkd_main_list + pkd_rest_list,
        "board": board_members,
        "board_organ_name": organ_name,
        "supervisory": supervisory,
        "capital": capital,
        "shareholders": shareholders,
        "registration_date": reg_date_str,
        "nip": nip_from_krs,
    }

    return OsintResult(
        source="ekrs", nip=nip, name=name or None, city=city or None,
        pkd=pkd_code[:5] if pkd_code else None, pkd_desc=pkd_desc or None,
        years_active=years_active, krs=krs or None, regon=regon or None,
        raw=enriched_raw,
    )


def _ekrs_last(arr: list, key: str) -> str:
    """Extract the latest (non-deleted) value from an eKRS array-of-dicts field."""
    if not arr:
        return ""
    for entry in reversed(arr):
        if entry.get("nrWpisuWykr"):
            continue  # this entry was deleted
        val = entry.get(key, "")
        if val:
            return str(val) if not isinstance(val, dict) else ""
    # Fall back to the absolute last entry
    last = arr[-1].get(key, "")
    return str(last) if not isinstance(last, dict) else ""


def _ekrs_person(member: dict) -> dict:
    """Parse a person entry from eKRS sklad/wspolnicy (array-based nested format)."""
    imiona_list = member.get("imiona", [])
    nazwisko_list = member.get("nazwisko", [])
    funkcja_list = member.get("funkcjaWOrganie", [])

    imie = ""
    if imiona_list:
        latest = imiona_list[-1]
        im = latest.get("imiona", {})
        if isinstance(im, dict):
            parts = [im.get("imie", ""), im.get("imieDrugie", "")]
            imie = " ".join(p for p in parts if p)
        else:
            imie = str(im)

    nazwisko = ""
    if nazwisko_list:
        latest = nazwisko_list[-1]
        nw = latest.get("nazwisko", {})
        if isinstance(nw, dict):
            nazwisko = nw.get("nazwiskoICzlon", "")
        else:
            nazwisko = str(nw)

    funkcja = ""
    if funkcja_list:
        funkcja = funkcja_list[-1].get("funkcjaWOrganie", "")

    full_name = f"{imie} {nazwisko}".strip()
    # If no person name, try company name (for institutional shareholders)
    if not full_name:
        nazwa_list = member.get("nazwa", [])
        if nazwa_list:
            full_name = _ekrs_last(nazwa_list, "nazwa")

    return {"name": full_name, "function": funkcja}


# ── CEIDG ─────────────────────────────────────────────────────────────

async def fetch_ceidg(nip: str) -> OsintResult:
    if not settings.ceidg_api_key:
        return OsintResult(source="ceidg", nip=nip, raw={"error": "no_api_key"})

    url = "https://dane.biznes.gov.pl/api/ceidg/v2/firmy"
    headers = {"Authorization": f"Bearer {settings.ceidg_api_key}"}
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(url, params={"nip": nip}, headers=headers)
        if resp.status_code == 404:
            return OsintResult(source="ceidg", nip=nip, raw={"error": "not_found"})
        resp.raise_for_status()
        data = resp.json()

    firmy = data.get("firmy", [])
    if not firmy:
        return OsintResult(source="ceidg", nip=nip, raw=data)

    firma = firmy[0]
    name = firma.get("nazwa", "")
    owner = firma.get("wlasciciel", {})
    full_name = f"{owner.get('imie', '')} {owner.get('nazwisko', '')}".strip()
    if not name and full_name:
        name = full_name
    adres = firma.get("adresDzialalnosci", {})
    city = adres.get("miasto", "")
    pkd_list = firma.get("pkd", [])
    pkd_main = pkd_list[0].get("kod", "") if pkd_list else ""

    start_date_str = firma.get("dataRozpoczeciaDzialalnosci", "")
    years_active = None
    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str[:10], "%Y-%m-%d")
            years_active = round((datetime.now() - start_date).days / 365.25, 1)
        except ValueError:
            pass

    website = firma.get("adresStronyInternetowej", "")
    return OsintResult(
        source="ceidg", nip=nip, name=name or None, city=city or None,
        pkd=pkd_main or None, years_active=years_active, website=website or None, raw=data,
    )


# ── Enrichment ────────────────────────────────────────────────────────

async def enrich_lead(nip: str) -> tuple[list[OsintResult], dict]:
    """Fetch all OSINT sources. Chain: VAT → GUS (PKD+KRS) → eKRS (by KRS) → CEIDG.

    After fetching, estimates employees/revenue from share capital, supervisory
    board presence, company age and PKD when registries don't provide them.
    """
    results: list[OsintResult] = []

    # Step 1: VAT White List first
    vat_result = await _safe_fetch(fetch_vat_whitelist, "vat_whitelist", nip)
    results.append(vat_result)

    # Step 2: GUS (gives us PKD, KRS, legal form)
    gus_result = await _safe_fetch(fetch_gus, "gus", nip)
    results.append(gus_result)

    # Step 3: eKRS — use KRS from VAT or GUS for reliable lookup
    krs_number = vat_result.krs or gus_result.krs
    try:
        ekrs_result = await fetch_ekrs(nip, krs_number=krs_number)
        results.append(ekrs_result)
    except Exception as exc:
        logger.warning("OSINT fetch ekrs failed for NIP %s: %s", nip, exc)
        results.append(OsintResult(source="ekrs", nip=nip, raw={"error": str(exc)}))

    # Step 4: CEIDG (for sole proprietors)
    ceidg_result = await _safe_fetch(fetch_ceidg, "ceidg", nip)
    results.append(ceidg_result)

    merged = _merge_results(results)

    # Step 5: Estimate employees/revenue from available signals
    _estimate_company_size(results, merged)

    return results, merged


async def _safe_fetch(fetcher, source_name: str, nip: str) -> OsintResult:
    try:
        return await fetcher(nip)
    except Exception as exc:
        logger.warning("OSINT fetch %s failed for NIP %s: %s", source_name, nip, exc)
        return OsintResult(source=source_name, nip=nip, raw={"error": str(exc)})


def _merge_results(results: list[OsintResult]) -> dict:
    fields: dict = {}
    merge_keys = ["name", "city", "employees", "revenue_pln", "pkd", "pkd_desc",
                  "years_active", "vat_status", "website", "regon", "krs"]
    for key in merge_keys:
        for r in results:
            val = getattr(r, key, None)
            if val is not None:
                fields[key] = val
                break

    # Extract voivodeship from parsed data (eKRS or GUS)
    for r in results:
        if r.raw and "_parsed" in r.raw:
            voi = r.raw["_parsed"].get("voivodeship")
            if voi:
                fields["voivodeship"] = voi
                break

    return fields


# ── Company size estimation ───────────────────────────────────────

def _estimate_company_size(results: list[OsintResult], merged: dict) -> None:
    """Estimate employees and revenue_pln from indirect signals when registries
    don't provide them directly.  Mutates *merged* in-place.

    Signals used:
    - Share capital (from eKRS) — large capital ≈ large company
    - Supervisory board presence — legally required for sp. z o.o.
      when emp>50 or capital>25M or revenue>50M
    - Company age (years_active)
    - PKD code (construction vs services vs trade)
    """
    if merged.get("employees") and merged.get("revenue_pln"):
        return  # already have real data

    # Collect signals from eKRS parsed data
    capital_value = 0.0
    has_supervisory = False
    for r in results:
        if r.source == "ekrs" and r.raw and "_parsed" in r.raw:
            parsed = r.raw["_parsed"]
            cap_str = parsed.get("capital", "") or ""
            capital_value = _parse_capital(cap_str)
            supervisory_list = parsed.get("supervisory", [])
            has_supervisory = bool(supervisory_list and len(supervisory_list) > 0)

    years = merged.get("years_active") or 0
    pkd = merged.get("pkd") or ""

    employees_est = 0
    revenue_est = 0.0

    # Capital-based estimation
    if capital_value >= 10_000_000:
        employees_est = max(employees_est, 200)
        revenue_est = max(revenue_est, 50_000_000)
    elif capital_value >= 5_000_000:
        employees_est = max(employees_est, 100)
        revenue_est = max(revenue_est, 20_000_000)
    elif capital_value >= 1_000_000:
        employees_est = max(employees_est, 50)
        revenue_est = max(revenue_est, 10_000_000)
    elif capital_value >= 200_000:
        employees_est = max(employees_est, 20)
        revenue_est = max(revenue_est, 5_000_000)
    elif capital_value >= 50_000:
        employees_est = max(employees_est, 10)
        revenue_est = max(revenue_est, 2_000_000)

    # Supervisory board → at least 50 employees (legal requirement for sp. z o.o.)
    if has_supervisory:
        employees_est = max(employees_est, 50)
        revenue_est = max(revenue_est, 10_000_000)

    # Age-based adjustment
    if years > 20:
        employees_est = max(employees_est, 30)
        revenue_est = max(revenue_est, 5_000_000)
    elif years > 10:
        employees_est = max(employees_est, 15)
        revenue_est = max(revenue_est, 3_000_000)
    elif years > 5:
        employees_est = max(employees_est, 10)
        revenue_est = max(revenue_est, 2_000_000)

    # PKD-based adjustment: construction (41-43) tends to have more employees
    pkd_prefix = pkd[:2] if pkd else ""
    if pkd_prefix in ("41", "42", "43"):
        employees_est = int(employees_est * 1.3)
        revenue_est = revenue_est * 1.2

    if not merged.get("employees") and employees_est > 0:
        merged["employees"] = employees_est
    if not merged.get("revenue_pln") and revenue_est > 0:
        merged["revenue_pln"] = revenue_est


def _parse_capital(capital_str: str) -> float:
    """Parse capital like '8426000,00 PLN' or '8426000.00' to float."""
    if not capital_str:
        return 0.0
    cleaned = re.sub(r"[^\d,.]", "", capital_str)
    cleaned = cleaned.replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


# ── Helpers ───────────────────────────────────────────────────────────

def _deep_get(d, *keys):
    for key in keys:
        if isinstance(d, dict):
            d = d.get(key, {})
        elif isinstance(d, list) and isinstance(key, int) and key < len(d):
            d = d[key]
        else:
            return None
    return d if d != {} else None


def _xml_value(xml: str, tag: str) -> str:
    match = re.search(rf"<{tag}>(.*?)</{tag}>", xml)
    return match.group(1).strip() if match else ""
