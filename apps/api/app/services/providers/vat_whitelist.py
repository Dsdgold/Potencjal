"""
MF VAT White List (Biała Lista) API connector.
Official API: https://wl-api.mf.gov.pl
Public, no auth required. Rate limit: ~10 req/s recommended.
"""

import httpx
import structlog
from datetime import date
from tenacity import retry, stop_after_attempt, wait_exponential
from app.services.providers.base import BaseProvider, ProviderResult
from app.config import get_settings

logger = structlog.get_logger()


class VATWhitelistProvider(BaseProvider):
    name = "vat_whitelist"
    display_name = "Biała Lista VAT (MF)"

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def fetch(self, nip: str, credentials: dict | None = None) -> ProviderResult:
        settings = get_settings()
        url = f"{settings.VAT_API_BASE_URL}/api/search/nip/{nip}"
        params = {"date": date.today().isoformat()}

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(url, params=params)

            if resp.status_code == 400:
                return ProviderResult(
                    provider_name=self.name, success=False,
                    error="Nieprawidłowy NIP lub brak danych w Białej Liście"
                )

            resp.raise_for_status()
            data = resp.json()

            result = data.get("result", {})
            subject = result.get("subject")

            if not subject:
                # Try subjects list (search response format)
                subjects = result.get("subjects", [])
                subject = subjects[0] if subjects else None

            if not subject:
                return ProviderResult(
                    provider_name=self.name, success=False,
                    error="Nie znaleziono podmiotu w Białej Liście VAT"
                )

            normalized = self.normalize(subject)
            return ProviderResult(
                provider_name=self.name,
                success=True,
                raw_data=subject,
                normalized_data=normalized,
            )

        except httpx.TimeoutException:
            logger.warning("vat_whitelist_timeout", nip=nip)
            return ProviderResult(provider_name=self.name, success=False, error="Timeout API MF")
        except Exception as e:
            logger.error("vat_whitelist_error", nip=nip, error=str(e))
            return ProviderResult(provider_name=self.name, success=False, error=str(e))

    def normalize(self, raw: dict) -> dict:
        accounts = raw.get("accountNumbers") or []
        reps = raw.get("representatives") or []
        partners = raw.get("partners") or []

        # Detect legal form from name
        name = (raw.get("name") or "").upper()
        legal_form = None
        if "SPÓŁKA AKCYJNA" in name or "S.A." in name:
            legal_form = "Spółka akcyjna"
        elif "SP. Z O.O." in name or "SPÓŁKA Z OGRANICZONĄ" in name:
            legal_form = "Spółka z o.o."
        elif "SP.K." in name or "KOMANDYTOWA" in name:
            legal_form = "Spółka komandytowa"
        elif "SP.J." in name or "JAWNA" in name:
            legal_form = "Spółka jawna"
        elif "S.C." in name:
            legal_form = "Spółka cywilna"

        # Parse address for city
        address = raw.get("workingAddress") or raw.get("residenceAddress") or ""
        city = self._extract_city(address)

        return {
            "name": raw.get("name"),
            "nip": raw.get("nip"),
            "regon": raw.get("regon"),
            "krs": raw.get("krs"),
            "legal_form": legal_form,
            "vat_status": raw.get("statusVat"),
            "vat_status_date": raw.get("registrationLegalDate"),
            "registered_address": raw.get("residenceAddress"),
            "business_address": raw.get("workingAddress"),
            "city": city,
            "registration_date": raw.get("registrationLegalDate"),
            "representatives": [{"name": r, "source": "vat_whitelist"} for r in reps] if reps else None,
            "partners": [{"name": p, "source": "vat_whitelist"} for p in partners] if partners else None,
            "bank_accounts": accounts[:5] if accounts else None,  # Limit for display
            "bank_account_count": len(accounts),
            "is_active": raw.get("statusVat") == "Czynny",
            "has_vat_registration": raw.get("statusVat") in ("Czynny", "Zwolniony"),
            "is_in_krs": bool(raw.get("krs")),
        }

    def _extract_city(self, address: str) -> str | None:
        if not address:
            return None
        parts = address.split(",")
        for part in reversed(parts):
            cleaned = part.strip()
            # City is usually after postal code or last meaningful part
            if cleaned and not any(c.isdigit() for c in cleaned[:3]):
                return cleaned
        return None
