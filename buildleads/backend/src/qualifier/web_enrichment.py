"""Web enrichment — scrapes company website + Google for description, contacts, social media.

Extracts:
  - Company description from meta tags and page content
  - Email addresses
  - Phone numbers
  - Social media links (LinkedIn, Facebook, Twitter/X, Instagram)
  - Physical address details
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

import httpx

logger = logging.getLogger(__name__)
TIMEOUT = httpx.Timeout(12.0, connect=5.0)

# Patterns
EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", re.ASCII)
PHONE_RE = re.compile(
    r"(?:\+48[\s\-]?)?\(?\d{2,3}\)?[\s\-]?\d{2,3}[\s\-]?\d{2,4}[\s\-]?\d{0,4}"
)
SOCIAL_PATTERNS = {
    "linkedin": re.compile(r"https?://(?:www\.)?linkedin\.com/(?:company|in)/[^\s\"'<>]+", re.I),
    "facebook": re.compile(r"https?://(?:www\.)?facebook\.com/[^\s\"'<>]+", re.I),
    "twitter": re.compile(r"https?://(?:www\.)?(?:twitter\.com|x\.com)/[^\s\"'<>]+", re.I),
    "instagram": re.compile(r"https?://(?:www\.)?instagram\.com/[^\s\"'<>]+", re.I),
    "youtube": re.compile(r"https?://(?:www\.)?youtube\.com/[^\s\"'<>]+", re.I),
}

# Junk email patterns to exclude
JUNK_EMAIL_RE = re.compile(
    r"(noreply|no-reply|webmaster|postmaster|hostmaster|mailer-daemon|example\.(com|pl))",
    re.I,
)


@dataclass
class WebEnrichResult:
    description: str | None = None
    emails: list[str] = field(default_factory=list)
    phones: list[str] = field(default_factory=list)
    social_media: dict[str, str] = field(default_factory=dict)
    meta_title: str | None = None
    meta_keywords: str | None = None
    address_snippet: str | None = None
    error: str | None = None


class _MetaParser(HTMLParser):
    """Lightweight HTML parser for meta tags, title, and body text."""

    def __init__(self):
        super().__init__()
        self.title = ""
        self.meta_description = ""
        self.meta_keywords = ""
        self.og_description = ""
        self._in_title = False
        self._body_text: list[str] = []
        self._in_body = False
        self._skip_tags = {"script", "style", "noscript", "svg", "nav", "footer", "header"}
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]):
        attrdict = {k.lower(): (v or "") for k, v in attrs}
        if tag == "title":
            self._in_title = True
        elif tag == "body":
            self._in_body = True
        elif tag == "meta":
            name = attrdict.get("name", "").lower()
            prop = attrdict.get("property", "").lower()
            content = attrdict.get("content", "")
            if name == "description" and content:
                self.meta_description = content
            elif name == "keywords" and content:
                self.meta_keywords = content
            elif prop in ("og:description", "twitter:description") and content:
                self.og_description = content
        if tag in self._skip_tags:
            self._skip_depth += 1

    def handle_endtag(self, tag: str):
        if tag == "title":
            self._in_title = False
        if tag in self._skip_tags and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data: str):
        if self._in_title:
            self.title += data
        elif self._in_body and self._skip_depth == 0:
            text = data.strip()
            if text and len(text) > 2:
                self._body_text.append(text)

    def get_body_text(self, max_chars: int = 3000) -> str:
        full = " ".join(self._body_text)
        return full[:max_chars]


async def scrape_website(url: str) -> WebEnrichResult:
    """Fetch company website and extract description, contacts, social links."""
    result = WebEnrichResult()
    if not url:
        result.error = "no_url"
        return result

    # Ensure full URL
    if not url.startswith("http"):
        url = f"https://{url}"

    try:
        async with httpx.AsyncClient(
            timeout=TIMEOUT,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; BuildLeads/2.0; +https://buildleads.pl)",
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "pl,en;q=0.5",
            },
        ) as client:
            resp = await client.get(url)
            if resp.status_code >= 400:
                result.error = f"http_{resp.status_code}"
                return result
            html = resp.text

            # Also try /kontakt or /contact page for contact info
            contact_html = ""
            base = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
            for path in ["/kontakt", "/contact", "/kontakty", "/o-nas", "/about"]:
                try:
                    cr = await client.get(urljoin(base, path))
                    if cr.status_code == 200:
                        contact_html += cr.text
                        break
                except Exception:
                    pass

    except Exception as exc:
        result.error = str(exc)[:200]
        return result

    combined = html + " " + contact_html

    # Parse HTML for meta tags and text
    parser = _MetaParser()
    try:
        parser.feed(html)
    except Exception:
        pass

    result.meta_title = parser.title.strip() or None
    result.meta_keywords = parser.meta_keywords.strip() or None

    # Build description from meta, then body text
    desc = parser.meta_description or parser.og_description
    if not desc:
        body = parser.get_body_text(2000)
        # Take first 2 sentences
        sentences = re.split(r"[.!?]\s", body)
        desc = ". ".join(s.strip() for s in sentences[:3] if len(s.strip()) > 20)
    result.description = desc[:1000] if desc else None

    # Extract emails
    emails = set(EMAIL_RE.findall(combined))
    result.emails = sorted(
        e for e in emails
        if not JUNK_EMAIL_RE.search(e) and not e.endswith((".png", ".jpg", ".svg", ".gif"))
    )[:10]

    # Extract phones
    phones = set()
    for m in PHONE_RE.finditer(combined):
        phone = m.group().strip()
        digits = re.sub(r"[^\d+]", "", phone)
        if 9 <= len(digits) <= 13:
            phones.add(phone)
    result.phones = sorted(phones)[:5]

    # Extract social media links
    for platform, pattern in SOCIAL_PATTERNS.items():
        match = pattern.search(combined)
        if match:
            link = match.group().rstrip("\"'>;),.")
            result.social_media[platform] = link

    return result


async def google_search_description(company_name: str, city: str | None = None) -> str | None:
    """Search Google for company description (lightweight scrape of search snippets)."""
    query = company_name
    if city:
        query += f" {city}"
    query += " firma opis"

    try:
        async with httpx.AsyncClient(
            timeout=TIMEOUT,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept-Language": "pl,en;q=0.5",
            },
        ) as client:
            resp = await client.get(
                "https://www.google.com/search",
                params={"q": query, "hl": "pl", "num": 5},
            )
            if resp.status_code != 200:
                return None

            # Extract text snippets from search results
            html = resp.text
            # Google wraps snippets in various elements; extract visible text
            parser = _MetaParser()
            try:
                parser.feed(html)
            except Exception:
                pass

            body = parser.get_body_text(3000)
            # Remove Google boilerplate
            body = re.sub(r"(Szukaj|Ustawienia|Narzędzia|Wszystkie|Grafika|Filmy|Więcej)[\s,]*", "", body)
            sentences = re.split(r"[.!?]\s", body)
            useful = [s.strip() for s in sentences if len(s.strip()) > 30 and company_name.split()[0].lower() in s.lower()]
            if useful:
                return ". ".join(useful[:3])[:500]

    except Exception as exc:
        logger.warning("Google search failed for %s: %s", company_name, exc)

    return None


def generate_description_from_data(
    name: str,
    city: str | None = None,
    voivodeship: str | None = None,
    pkd: str | None = None,
    pkd_desc: str | None = None,
    years_active: float | None = None,
    legal_form: str | None = None,
    employees: int | None = None,
    vat_status: str | None = None,
    board_members: list[dict] | None = None,
    website_desc: str | None = None,
) -> str:
    """Generate company description from available structured data."""
    parts = []

    parts.append(f"{name}")
    if legal_form:
        parts.append(f"to {legal_form.lower()}")
    if city:
        location = f"z siedzibą w {city}"
        if voivodeship:
            location += f" (woj. {voivodeship})"
        parts.append(location)

    desc = " ".join(parts) + "."

    if pkd_desc:
        desc += f" Główna działalność: {pkd_desc}"
        if pkd:
            desc += f" (PKD {pkd})"
        desc += "."

    if years_active and years_active > 0:
        years_int = int(years_active)
        if years_int >= 1:
            desc += f" Firma działa na rynku od {years_int} lat."

    if employees:
        desc += f" Zatrudnia {employees} pracowników."

    if vat_status:
        desc += f" Status VAT: {vat_status}."

    if board_members:
        ceo = next((m for m in board_members if "prezes" in (m.get("function", "") or "").lower()), None)
        if ceo:
            desc += f" Prezes zarządu: {ceo['name']}."
        elif board_members:
            desc += f" Zarząd: {', '.join(m['name'] for m in board_members[:3])}."

    if website_desc:
        desc += f"\n\n{website_desc}"

    return desc.strip()
