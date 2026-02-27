"""Polish NIP (tax identification number) validation and formatting."""

NIP_WEIGHTS = [6, 5, 7, 2, 3, 4, 5, 6, 7]


def clean_nip(nip: str) -> str:
    """Remove whitespace and dashes from NIP string."""
    return nip.replace("-", "").replace(" ", "").strip()


def validate_nip(nip: str) -> bool:
    """
    Validate a Polish NIP number using the official checksum algorithm.
    Returns True if the NIP is valid, False otherwise.
    """
    cleaned = clean_nip(nip)
    if len(cleaned) != 10:
        return False
    if not cleaned.isdigit():
        return False
    if cleaned == "0" * 10:
        return False
    digits = [int(d) for d in cleaned]
    checksum = sum(d * w for d, w in zip(digits[:9], NIP_WEIGHTS)) % 11
    if checksum == 10:
        return False
    return checksum == digits[9]


def format_nip(nip: str) -> str:
    """Format NIP as XXX-XXX-XX-XX."""
    cleaned = clean_nip(nip)
    if len(cleaned) != 10:
        return cleaned
    return f"{cleaned[:3]}-{cleaned[3:6]}-{cleaned[6:8]}-{cleaned[8:10]}"
