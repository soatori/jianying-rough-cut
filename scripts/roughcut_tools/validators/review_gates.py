"""Shared provenance and recorded-human-review checks; never grant human authority."""

from __future__ import annotations

from typing import Any

PROVENANCE = ("script_generated", "agent_interpreted", "human_verified", "unavailable")
HUMAN_LISTENING = ("pending", "verified", "not_assessed", "unavailable")
VERDICT_SCOPES = ("evidence", "interpretation", "human_listening")


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def collect_review_gates(value: Any, errors: list[str]) -> dict[str, dict[str, Any]]:
    """Return effective gates by object path without modifying supplied evidence.

    A human verdict is an externally supplied attestation, not proof that this
    validator listened or authenticated a person. Script reports are not verdicts.
    """
    gates: dict[str, dict[str, Any]] = {}

    def visit(item: Any, path: str) -> None:
        if isinstance(item, list):
            for index, child in enumerate(item):
                visit(child, f"{path}[{index}]")
            return
        if not isinstance(item, dict):
            return
        label = path or "root"
        provenance = item.get("provenance", "unavailable")
        if provenance not in PROVENANCE:
            errors.append(f"{label}.provenance: invalid; expected one of {PROVENANCE}")
            provenance = "unavailable"
        verdict = item.get("human_verdict")
        valid_verdict = (
            isinstance(verdict, dict)
            and verdict.get("actor") == "human"
            and _nonempty(verdict.get("reviewer"))
            and verdict.get("verdict") in ("approved", "rejected")
            and verdict.get("scope") in VERDICT_SCOPES
            and _nonempty(verdict.get("evidence"))
        )
        if "human_verdict" in item and not valid_verdict:
            errors.append(f"{label}.human_verdict: requires actor=human, reviewer, verdict, scope and evidence")
        approved = valid_verdict and verdict.get("verdict") == "approved"
        if provenance == "human_verified" and not approved:
            errors.append(f"{label}.provenance: human_verified requires an approved human_verdict")
            provenance = "unavailable"
        listening = item.get("human_listening", "pending")
        if listening not in HUMAN_LISTENING:
            errors.append(f"{label}.human_listening: invalid; expected one of {HUMAN_LISTENING}")
            listening = "pending"
        if listening == "verified" and not (approved and verdict.get("scope") == "human_listening"):
            errors.append(f"{label}.human_listening: verified requires an approved human_verdict with scope=human_listening")
            listening = "pending"
        if "human_review" in item and not isinstance(item["human_review"], bool):
            errors.append(f"{label}.human_review: must be a boolean flag")
        flags = item.get("flags", [])
        flags = flags if isinstance(flags, list) else []
        required_listening = item.get("needs_listen") is True or "needs_listen" in flags
        if required_listening and listening in ("not_assessed", "unavailable"):
            errors.append(f"{label}.human_listening: required listening must remain pending until verified")
            listening = "pending"
        gates[label] = {
            "provenance": provenance,
            "human_listening": listening,
            "human_review": item.get("human_review") is True or "human_review" in flags,
        }
        for key, child in item.items():
            if key != "human_verdict":
                visit(child, f"{path}.{key}" if path else key)

    visit(value, "")
    return gates
