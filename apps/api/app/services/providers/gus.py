"""
GUS REGON/BIR1 API connector (placeholder with SOAP client).
Official API: https://api.stat.gov.pl/Home/RegonApi
Requires API key from GUS. SOAP-based protocol.
"""

import httpx
import structlog
from app.services.providers.base import BaseProvider, ProviderResult
from app.config import get_settings

logger = structlog.get_logger()

# SOAP envelope templates for BIR1
LOGIN_ENVELOPE = """<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope"
               xmlns:ns="http://CIS/BIR/PUBL/2014/07">
  <soap:Header xmlns:wsa="http://www.w3.org/2005/08/addressing">
    <wsa:Action>http://CIS/BIR/PUBL/2014/07/IUslugaBIRzworki/Zaloguj</wsa:Action>
    <wsa:To>{api_url}</wsa:To>
  </soap:Header>
  <soap:Body>
    <ns:Zaloguj><ns:pKluczUzytkownika>{api_key}</ns:pKluczUzytkownika></ns:Zaloguj>
  </soap:Body>
</soap:Envelope>"""

SEARCH_ENVELOPE = """<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope"
               xmlns:ns="http://CIS/BIR/PUBL/2014/07"
               xmlns:dat="http://CIS/BIR/PUBL/2014/07/DataContract">
  <soap:Header xmlns:wsa="http://www.w3.org/2005/08/addressing">
    <wsa:Action>http://CIS/BIR/PUBL/2014/07/IUslugaBIRzworki/DaneSzukajPodmioty</wsa:Action>
    <wsa:To>{api_url}</wsa:To>
  </soap:Header>
  <soap:Body>
    <ns:DaneSzukajPodmioty>
      <ns:pParametryWyszukiwania>
        <dat:Nip>{nip}</dat:Nip>
      </ns:pParametryWyszukiwania>
    </ns:DaneSzukajPodmioty>
  </soap:Body>
</soap:Envelope>"""


class GUSProvider(BaseProvider):
    name = "gus_regon"
    display_name = "GUS REGON (BIR1)"

    @property
    def required_credentials(self) -> list[str]:
        return ["api_key"]

    @property
    def is_feature_flagged(self) -> bool:
        return True

    async def fetch(self, nip: str, credentials: dict | None = None) -> ProviderResult:
        settings = get_settings()
        api_key = ""

        if credentials and credentials.get("api_key"):
            api_key = credentials["api_key"]
        elif settings.GUS_API_KEY:
            api_key = settings.GUS_API_KEY

        if not api_key:
            return ProviderResult(
                provider_name=self.name, success=False,
                error="Brak klucza API GUS — skonfiguruj w ustawieniach organizacji"
            )

        api_url = settings.GUS_API_URL

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                # Step 1: Login
                login_body = LOGIN_ENVELOPE.format(api_key=api_key, api_url=api_url)
                login_resp = await client.post(
                    api_url,
                    content=login_body,
                    headers={"Content-Type": "application/soap+xml; charset=utf-8"}
                )
                login_resp.raise_for_status()

                # Extract session ID from response
                sid = self._extract_sid(login_resp.text)
                if not sid:
                    return ProviderResult(
                        provider_name=self.name, success=False,
                        error="Nie udało się zalogować do API GUS"
                    )

                # Step 2: Search
                search_body = SEARCH_ENVELOPE.format(nip=nip, api_url=api_url)
                search_resp = await client.post(
                    api_url,
                    content=search_body,
                    headers={
                        "Content-Type": "application/soap+xml; charset=utf-8",
                        "sid": sid,
                    }
                )
                search_resp.raise_for_status()

                raw = self._parse_search_response(search_resp.text)
                if not raw:
                    return ProviderResult(
                        provider_name=self.name, success=False,
                        error="Nie znaleziono podmiotu w REGON"
                    )

                normalized = self.normalize(raw)
                return ProviderResult(
                    provider_name=self.name, success=True,
                    raw_data=raw, normalized_data=normalized,
                )

        except httpx.TimeoutException:
            return ProviderResult(provider_name=self.name, success=False, error="Timeout API GUS")
        except Exception as e:
            logger.error("gus_error", nip=nip, error=str(e))
            return ProviderResult(provider_name=self.name, success=False, error=str(e))

    def normalize(self, raw: dict) -> dict:
        return {
            "regon": raw.get("Regon"),
            "name": raw.get("Nazwa"),
            "voivodeship": raw.get("Wojewodztwo"),
            "city": raw.get("Miejscowosc"),
            "postal_code": raw.get("KodPocztowy"),
            "registered_address": f"{raw.get('Ulica', '')} {raw.get('NrNieruchomosci', '')}, "
                                  f"{raw.get('KodPocztowy', '')} {raw.get('Miejscowosc', '')}".strip(", "),
            "legal_form_code": raw.get("FormaPrawna_Kod"),
            "pkd_main_code": raw.get("DzijalnoscCechaDominujaca_Kod"),
            "employee_count_range": self._map_employee_range(raw.get("Regon9_ZakladPodstawowy", {})
                                                             .get("ZakladPodstawowy_Klasa", "")),
        }

    def _extract_sid(self, xml_text: str) -> str | None:
        import re
        match = re.search(r"<ZalogujResult>(.*?)</ZalogujResult>", xml_text)
        return match.group(1) if match else None

    def _parse_search_response(self, xml_text: str) -> dict | None:
        import re
        match = re.search(r"<DaneSzukajPodmiotyResult>(.*?)</DaneSzukajPodmiotyResult>", xml_text, re.DOTALL)
        if not match:
            return None
        # Parse the inner XML (simplified)
        inner = match.group(1)
        result = {}
        for field_match in re.finditer(r"<(\w+)>(.*?)</\1>", inner):
            result[field_match.group(1)] = field_match.group(2)
        return result if result else None

    @staticmethod
    def _map_employee_range(code: str) -> str | None:
        mapping = {
            "1": "0-9", "2": "10-49", "3": "50-249", "4": "250-999", "5": "1000+",
        }
        return mapping.get(code)
