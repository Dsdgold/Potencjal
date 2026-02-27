"""
KRS (Krajowy Rejestr Sądowy) public OpenAPI connector.
Official API: https://api-krs.ms.gov.pl
Public, no auth required. Documented at api-krs.ms.gov.pl.
"""

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential
from app.services.providers.base import BaseProvider, ProviderResult
from app.config import get_settings

logger = structlog.get_logger()


class KRSProvider(BaseProvider):
    name = "krs"
    display_name = "KRS (Rejestr Sądowy)"

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def fetch(self, nip: str, credentials: dict | None = None, krs_number: str | None = None) -> ProviderResult:
        """Fetch from KRS. Can use NIP or direct KRS number."""
        settings = get_settings()
        base = settings.KRS_API_BASE_URL

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                # If we have a KRS number, use it directly
                if krs_number:
                    url = f"{base}/OdpisPelny/{krs_number}"
                    params = {"rejestr": "P", "format": "json"}
                    resp = await client.get(url, params=params)
                else:
                    # Search by NIP (via OdpisPelny won't work; use public search)
                    # KRS API doesn't support direct NIP search in OdpisPelny
                    # We need the KRS number first (from VAT whitelist)
                    return ProviderResult(
                        provider_name=self.name, success=False,
                        error="Brak numeru KRS — wymagany do zapytania rejestru"
                    )

                if resp.status_code == 404:
                    return ProviderResult(
                        provider_name=self.name, success=False,
                        error="Nie znaleziono podmiotu w KRS"
                    )

                resp.raise_for_status()
                data = resp.json()
                normalized = self.normalize(data)

                return ProviderResult(
                    provider_name=self.name,
                    success=True,
                    raw_data=data,
                    normalized_data=normalized,
                )

        except httpx.TimeoutException:
            logger.warning("krs_timeout", nip=nip)
            return ProviderResult(provider_name=self.name, success=False, error="Timeout API KRS")
        except Exception as e:
            logger.error("krs_error", nip=nip, error=str(e))
            return ProviderResult(provider_name=self.name, success=False, error=str(e))

    def normalize(self, raw: dict) -> dict:
        result = {}
        try:
            dane = raw.get("odppisPelnyJSON", raw).get("dane", raw)

            # Section 1: Basic data
            dzial1 = dane.get("dzial1", {})
            podmiot = dzial1.get("danePodmiotu", {})

            result["legal_form"] = podmiot.get("formaPrawna")
            result["legal_form_code"] = podmiot.get("formaOrganizacyjna")

            if podmiot.get("identyfikatory"):
                ident = podmiot["identyfikatory"]
                result["nip"] = ident.get("nip")
                result["regon"] = ident.get("regon")
                result["krs"] = ident.get("numerKRS")

            # Address
            siedziba = dzial1.get("siedzibaIAdres", {}).get("adres", {})
            if siedziba:
                addr_parts = [
                    siedziba.get("ulica", ""),
                    siedziba.get("nrDomu", ""),
                    siedziba.get("nrLokalu", ""),
                ]
                street = " ".join(p for p in addr_parts if p).strip()
                city = siedziba.get("miejscowosc", "")
                postal = siedziba.get("kodPocztowy", "")
                result["city"] = city
                result["postal_code"] = postal
                result["registered_address"] = f"{street}, {postal} {city}".strip(", ")
                result["voivodeship"] = siedziba.get("wojewodztwo")

            # Section 2: Representatives
            dzial2 = dane.get("dzial2", {})
            organ = dzial2.get("organReprezentacji", {})
            sklad = organ.get("sklad", [])
            reps = []
            for member in sklad:
                name_parts = [member.get("imiona", ""), member.get("nazwisko", "")]
                full_name = " ".join(p for p in name_parts if p)
                reps.append({
                    "name": full_name,
                    "function": member.get("funkcjaWOrganie", ""),
                    "source": "krs",
                })
            if reps:
                result["representatives"] = reps

            # Section 3: PKD codes
            dzial3 = dane.get("dzial3", {})
            pkd_list = dzial3.get("przedmiotDzialalnosciPrzedsiebiorcy", {})
            pkd_glowny = pkd_list.get("przedmiotPrzewazajacejDzialalnosci", [])
            pkd_pozostale = pkd_list.get("przedmiotPozostalejDzialalnosci", [])

            pkd_codes = []
            for p in pkd_glowny:
                code = p.get("kodDzial", "") + "." + p.get("kodKlasa", "") + p.get("kodPodklasa", "")
                pkd_codes.append({"code": code.strip("."), "name": p.get("opis", ""), "main": True})
            for p in pkd_pozostale:
                code = p.get("kodDzial", "") + "." + p.get("kodKlasa", "") + p.get("kodPodklasa", "")
                pkd_codes.append({"code": code.strip("."), "name": p.get("opis", ""), "main": False})

            if pkd_codes:
                result["pkd_codes"] = pkd_codes
                main_pkd = [p for p in pkd_codes if p.get("main")]
                if main_pkd:
                    result["pkd_main_code"] = main_pkd[0]["code"]
                    result["pkd_main_name"] = main_pkd[0]["name"]

            # Section 4: Capital
            dzial4 = dane.get("dzial4", {})
            kapital = dzial4.get("informacjeOKapitale", {})
            if kapital:
                wysokosc = kapital.get("wysokoscKapitaluZakladowego", {})
                if wysokosc:
                    try:
                        result["share_capital"] = float(
                            str(wysokosc.get("wartosc", "0")).replace(",", ".").replace(" ", "")
                        )
                        result["share_capital_currency"] = wysokosc.get("waluta", "PLN")
                    except (ValueError, TypeError):
                        pass

            # Partners
            wspolnicy = dzial1.get("wspolnicySpKomandytowej", dzial1.get("wspolnicySpZOO", []))
            if isinstance(wspolnicy, list) and wspolnicy:
                partners = []
                for w in wspolnicy:
                    name_parts = [w.get("imiona", ""), w.get("nazwisko", w.get("nazwa", ""))]
                    partners.append({"name": " ".join(p for p in name_parts if p), "source": "krs"})
                result["partners"] = partners

        except Exception as e:
            logger.error("krs_normalize_error", error=str(e))

        return result
