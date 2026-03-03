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
    """GUS REGON — uses test environment if no production key configured.
    Performs: login → search by NIP → full report for PKD, KRS, legal form, founding date."""
    if settings.gus_api_key:
        api_key = settings.gus_api_key
        wsdl_url = GUS_PROD_URL
    else:
        api_key = GUS_TEST_KEY
        wsdl_url = GUS_TEST_URL

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
    """eKRS — tries KRS number first (from VAT/GUS), then NIP as fallback."""
    identifiers = []
    if krs_number and krs_number.strip():
        identifiers.append(krs_number.strip().zfill(10))  # KRS must be 10 digits
    identifiers.append(nip)

    data = None
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        for identifier in identifiers:
            url = f"https://api-krs.ms.gov.pl/api/krs/OdpisPelny/{identifier}"
            try:
                resp = await client.get(url, params={"rejestr": "P", "format": "json"})
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("odppisPelnyJSON"):
                        break
                    data = None
            except Exception as exc:
                logger.warning("eKRS lookup %s failed: %s", identifier, exc)

    if not data:
        return OsintResult(source="ekrs", nip=nip, raw={"error": "not_found"})

    dane = data.get("odppisPelnyJSON", {}).get("dane", {})
    dzial1 = dane.get("dzial1", {})
    dzial2 = dane.get("dzial2", {})
    dzial3 = dane.get("dzial3", {})

    name = _deep_get(dzial1, "danePodmiotu", "nazwa")
    krs = _deep_get(dzial1, "danePodmiotu", "numerKRS")
    regon = _deep_get(dzial1, "danePodmiotu", "numerREGON")
    nip_from_krs = _deep_get(dzial1, "danePodmiotu", "numerNIP")

    siedz = _deep_get(dzial1, "siedzibaIAdres", "adres") or {}
    city = siedz.get("miejscowosc", "")

    pkd_main_list = _deep_get(dzial1, "przedmiotDzialalnosci", "przedmiotPrzewazajacejDzialalnosci") or []
    pkd_rest_list = _deep_get(dzial1, "przedmiotDzialalnosci", "przedmiotPozostalejDzialalnosci") or []
    pkd_code = ""
    pkd_desc = ""
    if pkd_main_list and isinstance(pkd_main_list, list) and len(pkd_main_list) > 0:
        pkd_code = pkd_main_list[0].get("kod", "")
        pkd_desc = pkd_main_list[0].get("opis", "")

    reg_date_str = _deep_get(dzial1, "danePodmiotu", "dataRejestracji")
    years_active = None
    if reg_date_str:
        try:
            reg_date = datetime.strptime(reg_date_str, "%Y-%m-%d")
            years_active = round((datetime.now() - reg_date).days / 365.25, 1)
        except ValueError:
            pass

    legal_form = _deep_get(dzial1, "danePodmiotu", "formaPrawna")

    board_members = []
    organ_list = _deep_get(dzial2, "reprezentacja", "sklad") or []
    if isinstance(organ_list, list):
        for member in organ_list:
            name_parts = []
            if member.get("imiona"):
                name_parts.append(str(member["imiona"]))
            if member.get("nazwisko"):
                name_parts.append(str(member["nazwisko"]))
            board_members.append({
                "name": " ".join(name_parts) if name_parts else str(member.get("nazwa", "")),
                "function": member.get("funkcjaWOrganie", ""),
            })
    organ_name = _deep_get(dzial2, "reprezentacja", "nazwaOrganu")

    supervisory = []
    nadzor_list = _deep_get(dzial2, "nadzor", "sklad") or []
    if isinstance(nadzor_list, list):
        for member in nadzor_list:
            name_parts = []
            if member.get("imiona"):
                name_parts.append(str(member["imiona"]))
            if member.get("nazwisko"):
                name_parts.append(str(member["nazwisko"]))
            supervisory.append({
                "name": " ".join(name_parts) if name_parts else "",
                "function": member.get("funkcjaWOrganie", ""),
            })

    capital = _deep_get(dzial3, "kappiitalSpolki", "wysokoscKapitaluZakladowego") or \
              _deep_get(dzial3, "kappiitalSpolki", "wartoscKapitaluZakladowego") or \
              _deep_get(dzial3, "kapitalSpolki", "wysokoscKapitaluZakladowego")

    shareholders = []
    wspolnicy_list = _deep_get(dzial3, "wspolnicySpZoo") or []
    if isinstance(wspolnicy_list, list):
        for w in wspolnicy_list:
            name_parts = []
            if w.get("imiona"):
                name_parts.append(str(w["imiona"]))
            if w.get("nazwisko"):
                name_parts.append(str(w["nazwisko"]))
            sh_name = " ".join(name_parts) if name_parts else str(w.get("nazwa", ""))
            shares = w.get("posiadaneUdzialy", "")
            shareholders.append({"name": sh_name, "shares": str(shares) if shares else ""})

    enriched_raw = dict(data)
    enriched_raw["_parsed"] = {
        "legal_form": legal_form,
        "voivodeship": siedz.get("wojewodztwo", ""),
        "full_address": siedz,
        "pkd_main": {"code": pkd_code, "desc": pkd_desc} if pkd_code else None,
        "pkd_all": [{"code": p.get("kod", ""), "desc": p.get("opis", "")} for p in pkd_main_list + pkd_rest_list],
        "board": board_members,
        "board_organ_name": organ_name,
        "supervisory": supervisory,
        "capital": str(capital) if capital else None,
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
    """Fetch all OSINT sources. Chain: VAT → GUS (PKD+KRS) → eKRS (by KRS) → CEIDG."""
    results: list[OsintResult] = []

    # Step 1: VAT White List first
    vat_result = await _safe_fetch(fetch_vat_whitelist, "vat_whitelist", nip)
    results.append(vat_result)

    # Step 2: GUS (gives us PKD, KRS, legal form — works with test key!)
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
    return fields


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
