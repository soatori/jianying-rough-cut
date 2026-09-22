"""Compare a proposed rough cut against the human-reviewed final plan."""

from __future__ import annotations

from typing import Any

from .result import result

DESTRUCTIVE_ACTIONS = {"delete", "shorten", "reorder", "join"}


def _decisions(value: Any, name: str) -> tuple[dict[str, dict[str, Any]], list[str]]:
    if not isinstance(value, dict) or "decisions" not in value:
        return {}, [f"{name}.decisions is required"]
    rows = value.get("decisions")
    if not isinstance(rows, list):
        return {}, [f"{name}.decisions must be an array"]
    decisions: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    for index, item in enumerate(rows):
        if not isinstance(item, dict) or not item.get("id"):
            errors.append(f"{name}.decisions[{index}] must contain id")
            continue
        decision_id = str(item["id"])
        if decision_id in decisions:
            errors.append(f"{name}.decisions duplicates id {decision_id!r}")
        else:
            decisions[decision_id] = item
    return decisions, errors


def _feedback(final_plan: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    feedback = final_plan.get("learning_feedback", {})
    if not isinstance(feedback, dict):
        return [], [], []
    dictionary = feedback.get("dictionary_corrections", feedback.get("dictionary_suggestions", []))
    preferences = feedback.get("preference_suggestions", [])
    pending = feedback.get("pending_cases", [])
    confirmed_dictionary = []
    if isinstance(dictionary, list):
        for item in dictionary:
            if not isinstance(item, dict):
                continue
            confirmed = item.get("human_confirmed", item.get("confirmed"))
            approval = item.get("approval", item.get("review_status"))
            if confirmed is True or approval in {"approved", "human_confirmed"}:
                confirmed_dictionary.append(item)
    return (
        confirmed_dictionary,
        [item for item in preferences if isinstance(item, dict)] if isinstance(preferences, list) else [],
        [item for item in pending if isinstance(item, dict)] if isinstance(pending, list) else [],
    )


def build_retrospective_diff(proposal: Any, final_plan: Any) -> dict[str, Any]:
    if not isinstance(proposal, dict) or not isinstance(final_plan, dict):
        return result("roughcut_retrospective", input_errors=["proposal and final plan must be JSON objects"])
    final_workflow = final_plan.get("workflow") if isinstance(final_plan.get("workflow"), dict) else {}
    if final_workflow.get("content_pass") not in {"stable", "approved"}:
        return result("roughcut_retrospective", errors=["final plan workflow.content_pass must be stable or approved"])
    proposed, proposed_errors = _decisions(proposal, "proposal")
    final, final_errors = _decisions(final_plan, "final")
    errors = proposed_errors + final_errors
    restored: list[dict[str, Any]] = []
    missed: list[dict[str, Any]] = []
    changed: list[dict[str, Any]] = []
    unchanged: list[dict[str, Any]] = []
    for decision_id, item in proposed.items():
        final_item = final.get(decision_id)
        proposed_action = item.get("action")
        final_action = final_item.get("action") if final_item is not None else None
        if final_item is None:
            if proposed_action in DESTRUCTIVE_ACTIONS:
                restored.append({"id": decision_id, "proposal": item, "final": None, "kind": "restored_by_human", "suggestion": "raise review bar for this decision type"})
            continue
        if proposed_action != final_action:
            entry = {"id": decision_id, "proposal": item, "final": final_item, "proposal_action": proposed_action, "final_action": final_action}
            changed.append(entry)
            if proposed_action in DESTRUCTIVE_ACTIONS and final_action in {"keep", "review"}:
                restored.append({**entry, "kind": "restored_by_human", "suggestion": "raise review bar for this decision type"})
        else:
            unchanged.append({"id": decision_id, "proposal": item, "final": final_item, "kind": "unchanged"})
    for decision_id, item in final.items():
        if decision_id not in proposed and item.get("action") in DESTRUCTIVE_ACTIONS:
            missed.append({"id": decision_id, "final": item, "kind": "added_by_human", "suggestion": "add this pattern to future candidate scans"})

    dictionary_suggestions, preference_suggestions, pending_cases = _feedback(final_plan)
    for item in restored:
        preference_suggestions.append({"kind": "restored_decision", "decision_id": item["id"], "suggestion": item["suggestion"], "approval": "pending"})
        pending_cases.append({"kind": "restored_decision", "decision_id": item["id"], "reason": "human changed or omitted a destructive proposal", "approval": "pending"})
    for item in missed:
        preference_suggestions.append({"kind": "missed_decision", "decision_id": item["id"], "suggestion": item["suggestion"], "approval": "pending"})
        pending_cases.append({"kind": "missed_decision", "decision_id": item["id"], "reason": "human added a decision absent from the proposal", "approval": "pending"})
    fully_adopted: list[dict[str, Any]] = []
    if not errors and not restored and not missed and not changed:
        fully_adopted.append({"kind": "fully_adopted", "approval": "pending", "decision_ids": [item["id"] for item in unchanged]})
        preference_suggestions.append({"kind": "fully_adopted", "suggestion": "fully adopted", "approval": "pending"})
    return result(
        "roughcut_retrospective",
        data={
            "restored": restored,
            "missed": missed,
            "changed": changed,
            "unchanged": unchanged,
            "unchanged_ids": [item["id"] for item in unchanged],
            "fully_adopted": fully_adopted,
            "dictionary_suggestions": dictionary_suggestions,
            "preference_suggestions": preference_suggestions,
            "pending_cases": pending_cases,
        },
        errors=errors,
        summary={"restored_count": len(restored), "missed_count": len(missed), "changed_count": len(changed), "unchanged_count": len(unchanged), "fully_adopted_count": len(fully_adopted)},
    )
