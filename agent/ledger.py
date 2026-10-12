"""JSONL audit ledger with a SHA-256 hash chain."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

GENESIS_HASH = "0" * 64

_REQUIRED_FIELDS = frozenset({
    "ts",
    "agent_id",
    "run_id",
    "tool",
    "args_hash",
    "classification",
    "decision",
    "reason",
})


def _entry_hash(entry: dict) -> str:
    payload = {
        key: value
        for key, value in entry.items()
        if key != "hash"
    }
    canonical = json.dumps(
        payload,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def verify(path: Path) -> bool:
    """Check reasons, links and hashes in the existing file."""
    path = Path(path)

    try:
        content = path.read_text(encoding="utf-8")
        previous_hash = GENESIS_HASH

        for line in content.splitlines():
            entry = json.loads(line)

            if not isinstance(entry, dict):
                return False

            if not _REQUIRED_FIELDS.issubset(entry):
                return False

            reason = entry.get("reason")
            if not isinstance(reason, str) or not reason.strip():
                return False

            if entry.get("prev_hash") != previous_hash:
                return False

            if entry.get("hash") != _entry_hash(entry):
                return False

            previous_hash = entry["hash"]

        return True

    except (OSError, ValueError, TypeError):
        return False


def append(entry: dict, path: Path) -> dict:
    """Append one entry without modifying existing entries."""
    path = Path(path)
    record = dict(entry)

    missing = _REQUIRED_FIELDS.difference(record)
    if missing:
        raise ValueError(
            "Missing ledger fields: " + ", ".join(sorted(missing))
        )

    content = ""
    previous_hash = GENESIS_HASH

    if path.exists():
        if not verify(path):
            raise ValueError("Cannot append to an invalid ledger")

        content = path.read_text(encoding="utf-8")
        lines = content.splitlines()

        if lines:
            previous_hash = json.loads(lines[-1])["hash"]

    record["prev_hash"] = previous_hash
    record["hash"] = _entry_hash(record)

    serialized = json.dumps(
        record,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )

    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("a", encoding="utf-8", newline="\n") as handle:
        if content and not content.endswith("\n"):
            handle.write("\n")
        handle.write(serialized + "\n")

    return record
