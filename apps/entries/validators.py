"""
Format checks for Indian tax IDs. These check the shape only; they do not
confirm with the government (a real verification service comes later).
"""
import re

PAN_RE = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")
GSTIN_RE = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")


def clean_id(value):
    return (value or "").strip().upper().replace(" ", "")


def is_valid_pan(pan):
    """PAN: 5 letters, 4 digits, 1 letter, e.g. ABCDE1234F."""
    return bool(PAN_RE.match(pan))


def is_valid_gstin(gstin):
    """GSTIN: 2-digit state code + PAN + entity number + 'Z' + check character."""
    return bool(GSTIN_RE.match(gstin))
