"""Tool policy and simulated OBO authorization for Day24."""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

PRINCIPALS_FILE = (
    Path(__file__).resolve().parent.parent / "data" / "principals.json"
)


@dataclass(frozen=True)
class PolicyContext:
    data_classification: str
    request_purpose: str
    agent_owner: str
    delegation_depth: int
    egress_enabled: bool
    principal_id: str = ""
    requested_tool: str = ""
    agent_scopes: tuple[str, ...] = ()
    parent_scopes: tuple[str, ...] = ()
    expires_at: str = ""


def _scope_set(value) -> set[str] | None:
    if not isinstance(value, (list, tuple, set, frozenset)):
        return None
    if any(
        not isinstance(item, str) or not item.strip()
        for item in value
    ):
        return None
    return set(value)


def check(context: PolicyContext) -> tuple[bool, str]:
    if context.data_classification not in (
        "public", "internal", "restricted"
    ):
        return False, "Unknown data classification"

    if not isinstance(context.egress_enabled, bool):
        return False, "Invalid egress flag"

    if (
        context.data_classification == "restricted"
        and context.egress_enabled
    ):
        return (
            False,
            "Restricted data must not enter an egress-enabled operation",
        )

    if (
        not isinstance(context.agent_owner, str)
        or not context.agent_owner.strip()
    ):
        return False, "Missing agent owner"

    if (
        type(context.delegation_depth) is not int
        or context.delegation_depth < 0
    ):
        return False, "Invalid delegation depth"

    if (
        not isinstance(context.expires_at, str)
        or not context.expires_at
    ):
        return False, "Missing run expiry"

    try:
        expiry = datetime.fromisoformat(
            context.expires_at.replace("Z", "+00:00")
        )
    except ValueError:
        return False, "Invalid run expiry"

    if (
        expiry.tzinfo is None
        or expiry.utcoffset() != timedelta(0)
    ):
        return False, "Run expiry must include a UTC timezone"

    if expiry <= datetime.now(timezone.utc):
        return False, "Run has expired"

    if (
        not isinstance(context.principal_id, str)
        or not context.principal_id
    ):
        return False, "Missing principal"

    try:
        principals = json.loads(
            PRINCIPALS_FILE.read_text(encoding="utf-8")
        )
    except (OSError, ValueError):
        return False, "Trusted principal registry is unavailable"

    if not isinstance(principals, dict):
        return False, "Invalid trusted principal registry"

    principal = principals.get(context.principal_id)
    if not isinstance(principal, dict):
        return False, "Unknown principal"

    principal_tools = _scope_set(principal.get("allowed_tools"))
    purposes = _scope_set(principal.get("purposes"))

    if principal_tools is None or purposes is None:
        return False, "Invalid principal permissions"

    if not isinstance(context.request_purpose, str):
        return False, "Invalid request purpose"

    if context.request_purpose not in purposes:
        return (
            False,
            "Request purpose is not authorized for this principal",
        )

    if (
        not isinstance(context.requested_tool, str)
        or not context.requested_tool
    ):
        return False, "Missing requested tool"

    if context.requested_tool not in principal_tools:
        return (
            False,
            "Requested tool is not authorized for this principal",
        )

    agent_tools = _scope_set(context.agent_scopes)
    if (
        agent_tools is None
        or context.requested_tool not in agent_tools
    ):
        return False, "Requested tool is outside agent scopes"

    if context.delegation_depth > 0:
        parent_tools = _scope_set(context.parent_scopes)
        if (
            parent_tools is None
            or context.requested_tool not in parent_tools
        ):
            return False, "Delegated tool is outside parent scopes"

    if (
        context.requested_tool == "http_post"
        and not context.egress_enabled
    ):
        return False, "Network tool requires egress permission"

    return (
        True,
        "Principal, purpose, scopes and run expiry authorize this tool",
    )