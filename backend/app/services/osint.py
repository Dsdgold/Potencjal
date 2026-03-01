"""OSINT proxy – fetches data from Polish public registries.

Supported sources:
  - VAT White List (Biała Lista) – free, no key
  - eKRS (KRS API)               – free, no key
  - CEIDG                        – requires API key
  - GUS REGON (BIR1.1)           – requires API key
"""

from __future__ import annotations

import logging
import re
from datetime import datetime

import httpx

from app.config import settings
from app.schemas import LeadUpdate, OsintResult

logger = logging.getLogger(__name__)

TIMEOUT = httpx.Timeout(15.0, connect=5.0)


# ── VAT White List ────────────────────────────────────────────────────
# https://wl-api.mf.gov.pl – free, no auth

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

    return OsintResult(
        source="vat_whitelist",
        nip=nip,
        name=name or None,
        city=city or None,
        vat_status=vat_status,
        regon=regon or None,
        krs=krs or None,
        raw=data,
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


# ── eKRS (KRS API) ───────────────────────────────────────────────────
# https://api-krs.ms.gov.pl – free, no auth

async def fetch_ekrs(nip: str) -> OsintResult:
    url = f"https://api-krs.ms.gov.pl/api/krs/OdpisPelny/{nip}"
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(url, params={"rejestr": "P", "format": "json"})
        if resp.status_code == 404:
            return OsintResult(source="ekrs", nip=nip, raw={"error": "not_found"})
        resp.raise_for_status()
        data = resp.json()

    dane = data.get("odppisPelnyJSON", {}).get("dane", {})
    dzial1 = dane.get("dzial1", {})

    name = _deep_get(dzial1, "danePodmiotu", "nazwa")
    krs = _deep_get(dzial1, "danePodmiotu", "numerKRS")
    regon = _deep_get(dzial1, "danePodmiotu", "numerREGON")
    pkd_main = _deep_get(dzial1, "przedmiotDzialalnosci", "przedmiotPrzewazajacejDzialalnosci", 0, "kodDzial")
    pkd_code = _deep_get(dzial1, "przedmiotDzialalnosci", "przedmiotPrzewazajacejDzialalnosci", 0, "kod") or ""

    siedz = _deep_get(dzial1, "siedzibaIAdres", "adres") or {}
    city = siedz.get("miejscowosc", "")

    reg_date_str = _deep_get(dzial1, "danePodmiotu", "dataRejestracji")
    years_active = None
    if reg_date_str:
        try:
            reg_date = datetime.strptime(reg_date_str, "%Y-%m-%d")
            years_active = round((datetime.now() - reg_date).days / 365.25, 1)
        except ValueError:
            pass

    return OsintResult(
        source="ekrs",
        nip=nip,
        name=name or None,
        city=city or None,
        pkd=pkd_code[:5] if pkd_code else (pkd_main or None),
        years_active=years_active,
        krs=krs or None,
        regon=regon or None,
        raw=data,
    )


# ── CEIDG ─────────────────────────────────────────────────────────────
# https://dane.biznes.gov.pl/api/ceidg/v2 – requires API key

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
        source="ceidg",
        nip=nip,
        name=name or None,
        city=city or None,
        pkd=pkd_main or None,
        years_active=years_active,
        website=website or None,
        raw=data,
    )


# ── GUS REGON (BIR1.1) ───────────────────────────────────────────────
# SOAP API – requires key from https://api.stat.gov.pl/

async def fetch_gus(nip: str) -> OsintResult:
    if not settings.gus_api_key:
        return OsintResult(source="gus", nip=nip, raw={"error": "no_api_key"})

    wsdl_url = "https://wyszukiwarkaregon.stat.gov.pl/wsBIR/UslugaBIRzewn662.svc"

    # Login to get session ID
    login_body = f"""<?xml version="1.0" encoding="utf-8"?>
    <soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope"
                   xmlns:ns="http://CIS/BIR/PUBL/2014/07">
      <soap:Header xmlns:wsa="http://www.w3.org/2005/08/addressing">
        <wsa:Action>http://CIS/BIR/PUBL/2014/07/IUslugaBIR/Zaloguj</wsa:Action>
        <wsa:To>{wsdl_url}</wsa:To>
      </soap:Header>
      <soap:Body>
        <ns:Zaloguj><ns:pKluczUzytkownika>{settings.gus_api_key}</ns:pKluczUzytkownika></ns:Zaloguj>
      </soap:Body>
    </soap:Envelope>"""

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        login_resp = await client.post(
            wsdl_url,
            content=login_body,
            headers={"Content-Type": "application/soap+xml; charset=utf-8"},
        )
        login_resp.raise_for_status()

        sid_match = re.search(r"<ZalogujResult>(.*?)</ZalogujResult>", login_resp.text)
        if not sid_match or not sid_match.group(1):
            return OsintResult(source="gus", nip=nip, raw={"error": "login_failed"})
        sid = sid_match.group(1)

        # Search by NIP
        search_body = f"""<?xml version="1.0" encoding="utf-8"?>
        <soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope"
                       xmlns:ns="http://CIS/BIR/PUBL/2014/07"
                       xmlns:dat="http://CIS/BIR/PUBL/2014/07/DataContract">
          <soap:Header xmlns:wsa="http://www.w3.org/2005/08/addressing">
            <wsa:Action>http://CIS/BIR/PUBL/2014/07/IUslugaBIR/DaneSzukajPodmioty</wsa:Action>
            <wsa:To>{wsdl_url}</wsa:To>
          </soap:Header>
          <soap:Body>
            <ns:DaneSzukajPodmioty>
              <ns:pParametryWyszukiwania>
                <dat:Nip>{nip}</dat:Nip>
              </ns:pParametryWyszukiwania>
            </ns:DaneSzukajPodmioty>
          </soap:Body>
        </soap:Envelope>"""

        search_resp = await client.post(
            wsdl_url,
            content=search_body,
            headers={
                "Content-Type": "application/soap+xml; charset=utf-8",
                "sid": sid,
            },
        )
        search_resp.raise_for_status()

    name = _xml_value(search_resp.text, "Nazwa")
    city = _xml_value(search_resp.text, "Miejscowosc")
    regon = _xml_value(search_resp.text, "Regon")
    pkd = _xml_value(search_resp.text, "PKDKod")

    return OsintResult(
        source="gus",
        nip=nip,
        name=name or None,
        city=city or None,
        regon=regon or None,
        pkd=pkd or None,
        raw={"response_snippet": search_resp.text[:2000]},
    )


# ── Enrichment (merge all sources) ───────────────────────────────────

async def enrich_lead(nip: str) -> tuple[list[OsintResult], LeadUpdate]:
    results: list[OsintResult] = []

    for fetcher in [fetch_vat_whitelist, fetch_ekrs, fetch_ceidg, fetch_gus]:
        try:
            result = await fetcher(nip)
            results.append(result)
        except Exception as exc:
            source_name = fetcher.__name__.replace("fetch_", "")
            logger.warning("OSINT fetch %s failed for NIP %s: %s", source_name, nip, exc)
            results.append(OsintResult(source=source_name, nip=nip, raw={"error": str(exc)}))

    merged = _merge_results(results)
    return results, merged


def _merge_results(results: list[OsintResult]) -> LeadUpdate:
    """Merge multiple OSINT results using first-non-null strategy."""
    fields: dict = {}
    merge_keys = ["name", "city", "employees", "revenue_pln", "pkd", "pkd_desc", "years_active", "vat_status", "website"]
    for key in merge_keys:
        for r in results:
            val = getattr(r, key, None)
            if val is not None:
                fields[key] = val
                break
    return LeadUpdate(**fields)


# ── Helpers ───────────────────────────────────────────────────────────

def _deep_get(d: dict, *keys):
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
