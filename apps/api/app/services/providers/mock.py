"""Mock provider for development and testing."""

import random
from app.services.providers.base import BaseProvider, ProviderResult

MOCK_COMPANIES = {
    "7740001454": {
        "name": "POLSKI KONCERN NAFTOWY ORLEN SPÓŁKA AKCYJNA",
        "nip": "7740001454", "regon": "610188201", "krs": "0000028860",
        "legal_form": "Spółka akcyjna",
        "vat_status": "Czynny",
        "registered_address": "ul. Chemików 7, 09-411 Płock",
        "business_address": "ul. Chemików 7, 09-411 Płock",
        "city": "Płock", "postal_code": "09-411", "voivodeship": "mazowieckie",
        "registration_date": "2001-08-23", "start_date": "1993-06-29",
        "share_capital": 1057000000.0, "share_capital_currency": "PLN",
        "annual_revenue_estimate": 280000000000.0,
        "employee_count_range": "1000+",
        "pkd_main_code": "19.20.Z",
        "pkd_main_name": "Wytwarzanie produktów rafinacji ropy naftowej",
        "pkd_codes": [
            {"code": "19.20.Z", "name": "Wytwarzanie produktów rafinacji ropy naftowej", "main": True},
            {"code": "46.71.Z", "name": "Sprzedaż hurtowa paliw", "main": False},
            {"code": "47.30.Z", "name": "Sprzedaż detaliczna paliw", "main": False},
        ],
        "representatives": [
            {"name": "Ireneusz Fąfara", "function": "Prezes Zarządu", "source": "mock"},
        ],
        "bank_accounts": ["PL12345678901234567890123456", "PL98765432109876543210987654"],
        "bank_account_count": 47,
        "is_active": True, "has_vat_registration": True, "is_in_krs": True,
    },
    "5252344078": {
        "name": "BUDIMEX SPÓŁKA AKCYJNA",
        "nip": "5252344078", "regon": "010732630", "krs": "0000001764",
        "legal_form": "Spółka akcyjna",
        "vat_status": "Czynny",
        "registered_address": "ul. Siedmiogrodzka 9, 01-204 Warszawa",
        "business_address": "ul. Siedmiogrodzka 9, 01-204 Warszawa",
        "city": "Warszawa", "postal_code": "01-204", "voivodeship": "mazowieckie",
        "registration_date": "2001-01-08", "start_date": "1968-04-01",
        "share_capital": 145848275.0, "share_capital_currency": "PLN",
        "annual_revenue_estimate": 8700000000.0,
        "employee_count_range": "1000+",
        "pkd_main_code": "41.20.Z",
        "pkd_main_name": "Roboty budowlane związane ze wznoszeniem budynków",
        "pkd_codes": [
            {"code": "41.20.Z", "name": "Roboty budowlane - budynki", "main": True},
            {"code": "42.11.Z", "name": "Roboty drogowe", "main": False},
            {"code": "43.99.Z", "name": "Roboty budowlane specjalistyczne", "main": False},
        ],
        "representatives": [
            {"name": "Artur Popko", "function": "Prezes Zarządu", "source": "mock"},
            {"name": "Jacek Daniewski", "function": "Wiceprezes Zarządu", "source": "mock"},
        ],
        "bank_accounts": ["PL11223344556677889900112233"],
        "bank_account_count": 12,
        "is_active": True, "has_vat_registration": True, "is_in_krs": True,
        "website": "https://www.budimex.pl",
        "recent_tenders": [
            {"title": "Budowa odcinka S7", "value": 450000000, "year": 2024},
            {"title": "Budowa szpitala powiatowego", "value": 89000000, "year": 2024},
        ],
    },
    "1132853869": {
        "name": "SIG SPÓŁKA Z OGRANICZONĄ ODPOWIEDZIALNOŚCIĄ",
        "nip": "1132853869", "regon": "362699468", "krs": "0000579589",
        "legal_form": "Spółka z o.o.",
        "vat_status": "Czynny",
        "registered_address": "ul. Postępu 12, 02-676 Warszawa",
        "business_address": "ul. Postępu 12, 02-676 Warszawa",
        "city": "Warszawa", "postal_code": "02-676", "voivodeship": "mazowieckie",
        "registration_date": "2015-10-14", "start_date": "2015-10-14",
        "share_capital": 5000.0, "share_capital_currency": "PLN",
        "annual_revenue_estimate": 500000000.0,
        "employee_count_range": "250-999",
        "pkd_main_code": "46.73.Z",
        "pkd_main_name": "Sprzedaż hurtowa drewna, materiałów budowlanych i wyposażenia sanitarnego",
        "pkd_codes": [
            {"code": "46.73.Z", "name": "Sprzedaż hurtowa materiałów budowlanych", "main": True},
            {"code": "46.74.Z", "name": "Sprzedaż hurtowa wyrobów metalowych oraz sprzętu", "main": False},
            {"code": "47.52.Z", "name": "Sprzedaż detaliczna drobnych wyrobów metalowych", "main": False},
        ],
        "representatives": [
            {"name": "Jan Kowalski", "function": "Prezes Zarządu", "source": "mock"},
            {"name": "Anna Nowak", "function": "Członek Zarządu", "source": "mock"},
        ],
        "bank_accounts": ["PL55667788990011223344556677"],
        "bank_account_count": 8,
        "is_active": True, "has_vat_registration": True, "is_in_krs": True,
        "website": "https://www.sig.pl",
    },
}


def _generate_random_company(nip: str) -> dict:
    """Generate plausible random company data for any NIP."""
    forms = [
        ("Spółka z o.o.", True, 50000),
        ("Spółka akcyjna", True, 500000),
        ("Jednoosobowa działalność gospodarcza", False, 0),
        ("Spółka komandytowa", True, 20000),
    ]
    form, has_krs, capital = random.choice(forms)
    cities = ["Warszawa", "Kraków", "Wrocław", "Poznań", "Gdańsk", "Katowice", "Łódź"]
    pkds = [
        ("41.20.Z", "Roboty budowlane związane ze wznoszeniem budynków"),
        ("43.11.Z", "Rozbiórka i przygotowanie terenu pod budowę"),
        ("46.73.Z", "Sprzedaż hurtowa drewna i materiałów budowlanych"),
        ("43.22.Z", "Wykonywanie instalacji wodno-kanalizacyjnych i cieplnych"),
        ("43.31.Z", "Tynkowanie"),
        ("71.12.Z", "Działalność w zakresie inżynierii"),
    ]
    pkd = random.choice(pkds)
    city = random.choice(cities)

    return {
        "name": f"FIRMA TESTOWA {nip[-4:]} SP. Z O.O.",
        "nip": nip, "regon": f"{random.randint(100000000, 999999999)}",
        "krs": f"0000{random.randint(100000, 999999)}" if has_krs else None,
        "legal_form": form,
        "vat_status": "Czynny",
        "registered_address": f"ul. Testowa {random.randint(1, 100)}, {random.randint(10, 99)}-{random.randint(100, 999)} {city}",
        "business_address": f"ul. Testowa {random.randint(1, 100)}, {random.randint(10, 99)}-{random.randint(100, 999)} {city}",
        "city": city, "voivodeship": "mazowieckie",
        "registration_date": f"{random.randint(2000, 2022)}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}",
        "share_capital": float(capital), "share_capital_currency": "PLN",
        "pkd_main_code": pkd[0], "pkd_main_name": pkd[1],
        "pkd_codes": [{"code": pkd[0], "name": pkd[1], "main": True}],
        "representatives": [{"name": "Jan Testowy", "function": "Prezes Zarządu", "source": "mock"}],
        "bank_accounts": [f"PL{random.randint(10**25, 10**26-1)}"],
        "bank_account_count": random.randint(1, 10),
        "is_active": True, "has_vat_registration": True, "is_in_krs": has_krs,
    }


class MockProvider(BaseProvider):
    name = "mock"
    display_name = "Mock (Dev/Test)"

    async def fetch(self, nip: str, credentials: dict | None = None) -> ProviderResult:
        data = MOCK_COMPANIES.get(nip, _generate_random_company(nip))
        return ProviderResult(
            provider_name=self.name,
            success=True,
            raw_data=data,
            normalized_data=data,  # Already in normalized format
        )

    def normalize(self, raw: dict) -> dict:
        return raw
