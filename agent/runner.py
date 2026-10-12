"""Separate ticket reading, private access and egress authorization."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from agent import ledger, pii, policy, tools

REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"
DEFAULT_LEDGER_PATH = REPORTS_DIR / "ledger.jsonl"
SINK_URL = "http://127.0.0.1:10024/reconcile"

ROOT_SCOPES = ("search_docs", "read_customer")
TICKET_NAME = re.compile(r"ticket-([0-9]+)(?:b)?\.md")
CUSTOMER_ID = re.compile(r"KH-[0-9]{6}")


class RunnerScaffoldPending(NotImplementedError):
    """Compatibility with dispatch tests; handle never raises this."""


def _args_hash(args: dict) -> str:
    canonical = json.dumps(
        args,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _run_a(message: str, llm, authorize):
    allowed = authorize(
        "search_docs",
        {"query": message},
        classification="internal",
        purpose="summarize-tickets",
    )
    if not allowed:
        return None

    docs = tools.search_docs(message)

    combined = "\n\n".join(doc["text"] for doc in docs)
    has_injection = llm.find_injection(combined) is not None

    ticket_ids = set()
    safe_docs = []

    for doc in docs:
        match = TICKET_NAME.fullmatch(doc["id"])
        if match:
            ticket_id = int(match.group(1))
            if ticket_id > 0:
                ticket_ids.add(ticket_id)

        safe_docs.append({
            "id": doc["id"],
            "text": pii.redact(doc["text"]),
        })

    return safe_docs, sorted(ticket_ids), has_injection


def _run_b(ticket_ids: list[int], authorize) -> None:
    if any(
        type(ticket_id) is not int or ticket_id <= 0
        for ticket_id in ticket_ids
    ):
        raise ValueError(
            "Run B accepts only positive integer ticket IDs"
        )

    if not ticket_ids:
        return

    # Authorize before opening the private store for ticket mapping.
    allowed = authorize(
        "read_customer",
        {
            "operation": "resolve_ticket_customers",
            "ticket_ids": ticket_ids,
        },
        classification="restricted",
        purpose="support-reply",
        operation="resolve_ticket_customers",
    )
    if not allowed:
        return

    customers = json.loads(
        tools.CUSTOMERS_FILE.read_text(encoding="utf-8")
    )
    if not isinstance(customers, list):
        raise ValueError("Invalid trusted customer registry")

    wanted = set(ticket_ids)
    customer_ids = set()

    for customer in customers:
        if not isinstance(customer, dict):
            raise ValueError("Invalid trusted customer record")

        related = customer.get("related_tickets")
        customer_id = customer.get("customer_id")

        if (
            not isinstance(related, list)
            or any(type(number) is not int for number in related)
            or not isinstance(customer_id, str)
            or CUSTOMER_ID.fullmatch(customer_id) is None
        ):
            raise ValueError("Invalid trusted ticket mapping")

        if wanted.intersection(related):
            customer_ids.add(customer_id)

    for customer_id in sorted(customer_ids):
        allowed = authorize(
            "read_customer",
            {"customer_id": customer_id},
            classification="restricted",
            purpose="support-reply",
        )

        if allowed:
            # Keep private records inside Run B.
            tools.read_customer(customer_id)


def handle(
    message: str,
    llm,
    log_dir: Path | None = None,
    principal_id: str = "support_l1",
) -> str:
    ledger_path = (
        Path(log_dir) / "ledger.jsonl"
        if log_dir is not None
        else DEFAULT_LEDGER_PATH
    )

    session_id = uuid4().hex
    expires_at = (
        datetime.now(timezone.utc) + timedelta(minutes=5)
    ).isoformat()

    def authorize_for(
        run_name: str,
        scopes: tuple[str, ...],
    ):
        agent_id = f"lab24-agent/{session_id}/{run_name}"
        run_id = f"{session_id}/{run_name}"

        def authorize(
            tool: str,
            args: dict,
            *,
            classification: str,
            purpose: str,
            egress: bool = False,
            operation: str = "tool_call",
        ) -> bool:
            context = policy.PolicyContext(
                data_classification=classification,
                request_purpose=purpose,
                agent_owner=agent_id,
                delegation_depth=1,
                egress_enabled=egress,
                principal_id=principal_id,
                requested_tool=tool,
                agent_scopes=scopes,
                parent_scopes=ROOT_SCOPES,
                expires_at=expires_at,
            )

            allowed, reason = policy.check(context)

            if not isinstance(allowed, bool):
                raise RuntimeError(
                    "Policy returned an invalid decision"
                )

            if (
                not isinstance(reason, str)
                or not reason.strip()
            ):
                raise RuntimeError(
                    "Policy returned an empty reason"
                )

            ledger.append(
                {
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "agent_id": agent_id,
                    "run_id": run_id,
                    "on_behalf_of": principal_id,
                    "expires_at": expires_at,
                    "tool": tool,
                    "operation": operation,
                    "args_hash": _args_hash(args),
                    "classification": classification,
                    "decision": "allow" if allowed else "deny",
                    "reason": reason,
                    "request_purpose": purpose,
                    "delegation_depth": context.delegation_depth,
                    "agent_scopes": list(scopes),
                    "parent_scopes": list(ROOT_SCOPES),
                    "egress_enabled": egress,
                },
                ledger_path,
            )

            return allowed

        return authorize

    result = _run_a(
        message,
        llm,
        authorize_for("run-a", ("search_docs",)),
    )

    if result is None:
        return "Yêu cầu tìm ticket bị từ chối bởi policy."

    safe_docs, ticket_ids, has_injection = result

    _run_b(
        ticket_ids,
        authorize_for("run-b", ("read_customer",)),
    )

    if has_injection:
        allowed = authorize_for(
            "egress-check",
            ("http_post",),
        )(
            "http_post",
            {"url": SINK_URL},
            classification="restricted",
            purpose="support-reply",
            egress=True,
            operation="injection_egress_request",
        )

        if allowed:
            raise RuntimeError(
                "Restricted egress was unexpectedly authorized"
            )

    return llm.summarize(safe_docs)