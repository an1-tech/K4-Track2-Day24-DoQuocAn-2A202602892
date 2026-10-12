"""PII detection and redaction for the synthetic Day24 lab."""
from __future__ import annotations

import re

_PATTERNS = (
    (
        "EMAIL",
        re.compile(
            r"(?P<value>[A-Za-z0-9._%+-]+@"
            r"[A-Za-z0-9.-]+\.[A-Za-z]{2,})"
        ),
    ),
    (
        "VN_BANK_ACCOUNT",
        re.compile(
            r"\b(?:STK|số\s+tài\s+khoản|so\s+tai\s+khoan|bank_account)\b"
            r"\s*[:=#-]?\s*(?P<value>[0-9]{8,16})(?!\w)",
            re.IGNORECASE,
        ),
    ),
    (
        "VN_CCCD",
        re.compile(r"(?<!\w)(?P<value>[0-9]{12})(?!\w)"),
    ),
    (
        "VN_PHONE",
        re.compile(
            r"(?<!\w)(?P<value>0(?:[ \t-]?[0-9]){9,10})(?!\w)"
        ),
    ),
)


def detect(text: str) -> list[dict]:
    """Return non-overlapping entities with offsets in the original text."""
    candidates = []

    for priority, (entity_type, pattern) in enumerate(_PATTERNS):
        for match in pattern.finditer(text):
            start, end = match.span("value")
            candidates.append((priority, start, end, entity_type))

    accepted = []
    for _, start, end, entity_type in sorted(candidates):
        overlaps = any(
            start < entity["end"] and entity["start"] < end
            for entity in accepted
        )
        if not overlaps:
            accepted.append(
                {"type": entity_type, "start": start, "end": end}
            )

    return sorted(accepted, key=lambda entity: entity["start"])


def redact(text: str) -> str:
    """Replace detected values from right to left to preserve offsets."""
    result = text
    for entity in reversed(detect(text)):
        replacement = f'[REDACTED_{entity["type"]}]'
        result = (
            result[:entity["start"]]
            + replacement
            + result[entity["end"]:]
        )
    return result
