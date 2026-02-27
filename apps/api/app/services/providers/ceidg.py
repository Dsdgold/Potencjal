"""
CEIDG (Centralna Ewidencja i Informacja o Działalności Gospodarczej) connector.
Official API: https://dane.biznes.gov.pl/api/ceidg/v2
Requires API key from dane.biznes.gov.pl.
"""

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential
from app.services.providers.base import BaseProvider, ProviderResult
from app.config import get_settings

logger = structlog.get_logger()


class CEIDGProvider(BaseProvider):
    name = "ceidg"
    display_name = "CEIDG"

    @property
    def required_credentials(self) -> list[str]:
        return ["api_key"]

    @property
    def is_feature_flagged(self) -> bool:
        return True

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def fetch(self, nip: str, credentials: dict | None = None) -> ProviderResult:
        settings = get_settings()
        api_key = ""

        if credentials and credentials.get("api_key"):
            api_key = credentials["api_key"]
        elif settings.CEIDG_API_KEY:
            api_key = settings.CEIDG_API_KEY

        if not api_key:
            return ProviderResult(
                provider_name=self.name, success=False,
                error="Brak klucza API CEIDG — skonfiguruj w ustawieniach"
            )

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                url = f"{settings.CEIDG_API_URL}/firmy"
                resp = await client.get(
                    url,
                    params={"nip": nip},
                    headers={"Authorization": f"Bearer {api_key}"}
                )

                if resp.status_code == 404:
                    return ProviderResult(
                        provider_name=self.name, success=False,
                        error="Nie znaleziono w CEIDG (firma nie jest JDG)"
                    )

                resp.raise_for_status()
                data = resp.json()

                firms = data.get("firmy", data if isinstance(data, list) else [data])
                if not firms:
                    return ProviderResult(
                        provider_name=self.name, success=False,
                        error="Brak wyników w CEIDG"
                    )

                raw = firms[0] if isinstance(firms, list) else firms
                normalized = self.normalize(raw)

                return ProviderResult(
                    provider_name=self.name, success=True,
                    raw_data=raw, normalized_data=normalized,
                )

        except httpx.TimeoutException:
            return ProviderResult(provider_name=self.name, success=False, error="Timeout API CEIDG")
        except Exception as e:
            logger.error("ceidg_error", nip=nip, error=str(e))
            return ProviderResult(provider_name=self.name, success=False, error=str(e))

    def normalize(self, raw: dict) -> dict:
        result = {
            "is_in_ceidg": True,
            "legal_form": "Jednoosobowa działalność gospodarcza",
        }

        if raw.get("nazwa"):
            result["name"] = raw["nazwa"]
        if raw.get("adresDzialalnosci"):
            addr = raw["adresDzialalnosci"]
            parts = [addr.get("ulica", ""), addr.get("budynek", ""), addr.get("lokal", "")]
            street = " ".join(p for p in parts if p)
            result["business_address"] = f"{street}, {addr.get('kod', '')} {addr.get('miasto', '')}".strip(", ")
            result["city"] = addr.get("miasto")
            result["postal_code"] = addr.get("kod")

        if raw.get("dataRozpoczeciaDzialalnosci"):
            result["start_date"] = raw["dataRozpoczeciaDzialalnosci"]

        if raw.get("pkd"):
            pkd_list = raw["pkd"] if isinstance(raw["pkd"], list) else [raw["pkd"]]
            result["pkd_codes"] = [{"code": p.get("kod", ""), "name": p.get("nazwa", ""), "main": p.get("przewazajace", False)}
                                   for p in pkd_list]
            main = [p for p in result["pkd_codes"] if p.get("main")]
            if main:
                result["pkd_main_code"] = main[0]["code"]
                result["pkd_main_name"] = main[0]["name"]

        if raw.get("email"):
            result["email"] = raw["email"]
        if raw.get("www"):
            result["website"] = raw["www"]
        if raw.get("telefon"):
            result["phone"] = raw["telefon"]

        status = raw.get("status", "")
        result["is_active"] = status.lower() in ("aktywny", "active", "1")

        return result
