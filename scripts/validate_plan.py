"""Validate an independent rough-cut content decision plan."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


ACTIONS = {"keep", "delete", "shorten", "reorder", "join", "review"}
DESTRUCTIVE_ACTIONS = {"delete", "shorten", "reorder", "join"}
PASSES = {"content", "refinement"}
CONFIDENCE = {"high", "medium", "low"}
DOMAIN_STATUS = {"identified", "uncertain", "not_applicable"}
REVIEW_FLAGS = {"needs_listen", "needs_context", "low_confidence", "human_review"}
REVIEW_REQUIRED_FLAGS = {"needs_context", "human_review", "low_confidence"}
REJECTED_FIELDS = {"execution_handoff", "keep_blocks"}
COMPLETENESS_STATUS = {"complete", "partial", "unknown"}
COMPLETENESS_IMPACT = {"none", "review_required"}
CONTENT_PHASE_STATUS = {"draft", "stable", "approved"}
REFINEMENT_PHASE_STATUS = {"not_started", "draft", "approved"}
ALIGNMENT_PHASE_STATUS = {"not_started", "draft", "stable", "approved"}
WORKFLOW_MODES = {"content_edit", "final_draft_audit"}
BOUNDARY_BASES = {
    "semantic_unit", "word_boundary", "phrase_boundary", "sentence_boundary",
    "pause", "waveform", "shot_boundary", "take_boundary", "manual_marker",
    "derived", "unknown",
}
BOUNDARY_PRECISION = {"exact", "approximate"}


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _validate_string_array(
    value: Any,
    prefix: str,
    errors: list[str],
    *,
    require_nonempty: bool = False,
) -> list[str]:
    if not isinstance(value, list):
        errors.append(prefix + " must be an array of non-empty strings")
        return []
    result: list[str] = []
    for index, item in enumerate(value):
        if not _nonempty_string(item):
            errors.append(f"{prefix}[{index}] must be a non-empty string")
        else:
            result.append(item)
    if require_nonempty and not result:
        errors.append(prefix + " must contain at least one non-empty string")
    return result


def _validate_range(
    item: dict[str, Any],
    prefix: str,
    timebase: str,
    duration: float | None,
    errors: list[str],
) -> None:
    start, end = item.get("start"), item.get("end")
    if not _is_number(start) or not _is_number(end) or end <= start or start < 0:
        errors.append(prefix + " has an invalid time range")
    elif duration is not None and end > duration:
        errors.append(prefix + " exceeds input duration")
    if item.get("timebase") != timebase:
        errors.append(prefix + ".timebase must match input.timebase")


def _validate_completeness(
    input_data: dict[str, Any],
    errors: list[str],
) -> str | None:
    completeness = input_data.get("completeness")
    if not isinstance(completeness, dict):
        errors.append("input.completeness must be an object")
        return None

    status = completeness.get("status")
    if status not in COMPLETENESS_STATUS:
        errors.append("input.completeness.status is invalid")
        status = None

    _validate_string_array(
        completeness.get("checked"),
        "input.completeness.checked",
        errors,
        require_nonempty=True,
    )
    missing = _validate_string_array(
        completeness.get("missing"),
        "input.completeness.missing",
        errors,
    )
    _validate_string_array(
        completeness.get("evidence"),
        "input.completeness.evidence",
        errors,
        require_nonempty=True,
    )

    impact = completeness.get("impact")
    if impact not in COMPLETENESS_IMPACT:
        errors.append("input.completeness.impact is invalid")
    if status == "complete" and missing:
        errors.append("input.completeness.missing must be empty when status is complete")
    if status == "partial" and not missing:
        errors.append("input.completeness.missing is required when status is partial")
    if status in {"partial", "unknown"} and impact != "review_required":
        errors.append(
            "input.completeness.impact must be review_required when material completeness is not complete"
        )
    return status


def _validate_workflow(
    plan: dict[str, Any],
    errors: list[str],
) -> tuple[str | None, str | None, str | None, str | None]:
    workflow = plan.get("workflow")
    if not isinstance(workflow, dict):
        errors.append("workflow must be an object")
        return None, None, None, None

    mode = workflow.get("mode", "content_edit")
    if mode not in WORKFLOW_MODES:
        errors.append("workflow.mode is invalid")
        mode = None
    if mode == "final_draft_audit" and workflow.get("text_authority") != "final_visible_subtitle":
        errors.append("workflow.text_authority must be final_visible_subtitle in final_draft_audit")

    content_status = workflow.get("content_pass")
    if content_status not in CONTENT_PHASE_STATUS:
        errors.append("workflow.content_pass is invalid")
        content_status = None

    refinement_status = workflow.get("refinement_pass")
    if refinement_status not in REFINEMENT_PHASE_STATUS:
        errors.append("workflow.refinement_pass is invalid")
        refinement_status = None

    if (
        refinement_status in {"draft", "approved"}
        and content_status not in {"stable", "approved"}
    ):
        errors.append(
            "workflow.refinement_pass requires workflow.content_pass to be stable or approved"
        )
    alignment_status = workflow.get("subtitle_alignment", "not_started")
    if alignment_status not in ALIGNMENT_PHASE_STATUS:
        errors.append("workflow.subtitle_alignment is invalid")
        alignment_status = None
    if alignment_status in {"stable", "approved"} and content_status not in {"stable", "approved"}:
        errors.append("workflow.subtitle_alignment requires workflow.content_pass to be stable or approved")
    return content_status, refinement_status, alignment_status, mode


def _validate_boundary(
    item: dict[str, Any],
    prefix: str,
    errors: list[str],
) -> str | None:
    boundary = item.get("boundary")
    if not isinstance(boundary, dict):
        errors.append(prefix + ".boundary must be an object")
        return None

    for field in ("start_basis", "end_basis"):
        value = boundary.get(field)
        if not isinstance(value, str) or value not in BOUNDARY_BASES:
            errors.append(prefix + f".boundary.{field} is invalid")

    _validate_string_array(
        boundary.get("evidence"),
        prefix + ".boundary.evidence",
        errors,
        require_nonempty=True,
    )
    precision = boundary.get("precision")
    if precision not in BOUNDARY_PRECISION:
        errors.append(prefix + ".boundary.precision is invalid")
        precision = None
    if "note" in boundary and not _nonempty_string(boundary.get("note")):
        errors.append(prefix + ".boundary.note must be a non-empty string")
    return precision


def _validate_orientation(
    plan: dict[str, Any],
    errors: list[str],
) -> tuple[str | None, float | None, bool, str | None]:
    input_data = plan.get("input")
    if not isinstance(input_data, dict):
        errors.append("input must be an object")
        return None, None, False, None

    timebase = input_data.get("timebase")
    if not _nonempty_string(timebase):
        errors.append("input.timebase is required")
        timebase = None

    duration = input_data.get("duration")
    if duration is not None and (not _is_number(duration) or duration <= 0):
        errors.append("input.duration must be a positive number when present")
        duration = None

    completeness_status = _validate_completeness(input_data, errors)

    theme = plan.get("theme_analysis")
    if not isinstance(theme, dict):
        errors.append("theme_analysis must be an object")
    else:
        for field in ("topic", "thesis", "purpose", "audience"):
            if not _nonempty_string(theme.get(field)):
                errors.append(f"theme_analysis.{field} is required")
        if theme.get("confidence") not in CONFIDENCE:
            errors.append("theme_analysis.confidence is invalid")

    domain = plan.get("domain_analysis")
    domain_unresolved = False
    if not isinstance(domain, dict):
        errors.append("domain_analysis must be an object")
        domain = {}
    if domain.get("status") not in DOMAIN_STATUS:
        errors.append("domain_analysis.status is invalid")
    if not _nonempty_string(domain.get("primary_domain")):
        errors.append("domain_analysis.primary_domain is required")
    if domain.get("confidence") not in CONFIDENCE:
        errors.append("domain_analysis.confidence is invalid")
    domain_unresolved = domain.get("status") == "uncertain" or domain.get("confidence") == "low"
    for field in ("segments", "terms", "entities", "protected_facts", "unresolved_terms"):
        if field in domain and not isinstance(domain[field], list):
            errors.append(f"domain_analysis.{field} must be a list")

    outline = plan.get("outline")
    if not isinstance(outline, dict):
        errors.append("outline must be an object")
    else:
        if outline.get("confidence") not in CONFIDENCE:
            errors.append("outline.confidence is invalid")
        units = outline.get("units")
        if not isinstance(units, list) or not units:
            errors.append("outline.units must be a non-empty list")
        else:
            for index, unit in enumerate(units):
                prefix = f"outline.units[{index}]"
                if not isinstance(unit, dict):
                    errors.append(prefix + " must be an object")
                    continue
                if not _nonempty_string(unit.get("id")):
                    errors.append(prefix + ".id is required")
                if not (_nonempty_string(unit.get("title")) or _nonempty_string(unit.get("summary"))):
                    errors.append(prefix + " requires title or summary")
                if not _nonempty_string(unit.get("role")):
                    errors.append(prefix + ".role is required")
                if unit.get("confidence") not in CONFIDENCE:
                    errors.append(prefix + ".confidence is invalid")
                if timebase is not None:
                    _validate_range(unit, prefix, timebase, duration, errors)

    speakers = plan.get("speakers")
    if not isinstance(speakers, list) or not speakers:
        errors.append("speakers must be a non-empty list")
    elif any(not isinstance(item, dict) for item in speakers):
        errors.append("speakers entries must be objects")
    if not isinstance(plan.get("protected_facts"), list):
        errors.append("protected_facts must be a list")

    return timebase, duration, domain_unresolved, completeness_status


def validate(plan: Any) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(plan, dict):
        return {"ok": False, "errors": ["plan must be a JSON object"], "warnings": []}

    if plan.get("version") != 1:
        errors.append("version must be 1")
    required = (
        "input", "evidence", "goal", "theme_analysis", "domain_analysis", "outline",
        "speakers", "original_structure", "recommended_structure", "decisions", "protected_facts",
        "workflow",
    )
    for key in required:
        if key not in plan:
            errors.append(f"missing top-level field: {key}")
    for key in REJECTED_FIELDS:
        if key in plan:
            errors.append(f"application-specific field is not allowed: {key}")
    if not isinstance(plan.get("evidence"), list):
        errors.append("evidence must be a list")
    if not isinstance(plan.get("goal"), dict):
        errors.append("goal must be an object")
    for key in ("original_structure", "recommended_structure"):
        if not isinstance(plan.get(key), list):
            errors.append(f"{key} must be a list")

    timebase, duration, domain_unresolved, completeness_status = _validate_orientation(plan, errors)
    content_phase_status, refinement_phase_status, alignment_phase_status, workflow_mode = _validate_workflow(plan, errors)
    decisions = plan.get("decisions", [])
    if not isinstance(decisions, list):
        errors.append("decisions must be a list")
        decisions = []

    ids: set[str] = set()
    for index, item in enumerate(decisions):
        prefix = f"decisions[{index}]"
        if not isinstance(item, dict):
            errors.append(prefix + " must be an object")
            continue
        decision_id = item.get("id")
        if not _nonempty_string(decision_id):
            errors.append(prefix + ".id is required")
        elif decision_id in ids:
            errors.append(prefix + f" duplicates id {decision_id}")
        else:
            ids.add(decision_id)
        decision_pass = item.get("pass")
        if decision_pass not in PASSES:
            errors.append(prefix + ".pass must be content or refinement")
        if item.get("action") not in ACTIONS:
            errors.append(prefix + ".action is invalid")
        if item.get("confidence") not in CONFIDENCE:
            errors.append(prefix + ".confidence is invalid")
        if not _nonempty_string(item.get("summary")):
            errors.append(prefix + ".summary is required")
        if not _nonempty_string(item.get("reason")):
            errors.append(prefix + ".reason is required")
        if not isinstance(item.get("domain_sensitive"), bool):
            errors.append(prefix + ".domain_sensitive must be boolean")
        flags = item.get("flags", [])
        flags_valid = isinstance(flags, list) and all(
            isinstance(flag, str) and flag in REVIEW_FLAGS for flag in flags
        )
        if not flags_valid:
            errors.append(prefix + ".flags contains an unknown value")
        flag_set = {
            flag for flag in flags
            if isinstance(flag, str) and flag in REVIEW_FLAGS
        } if isinstance(flags, list) else set()
        if timebase is not None:
            _validate_range(item, prefix, timebase, duration, errors)
        precision = _validate_boundary(item, prefix, errors)
        if decision_pass == "refinement":
            if content_phase_status not in {"stable", "approved"}:
                errors.append(
                    prefix + ".pass refinement requires workflow.content_pass to be stable or approved"
                )
            if refinement_phase_status == "not_started":
                errors.append(
                    prefix + ".pass refinement requires workflow.refinement_pass to be draft or approved"
                )
        if item.get("action") in DESTRUCTIVE_ACTIONS and precision == "approximate":
            if item.get("confidence") == "high":
                errors.append(
                    prefix + " cannot be high-confidence with approximate boundary precision"
                )
            elif not flag_set & REVIEW_REQUIRED_FLAGS:
                warnings.append(prefix + " should carry a review flag with approximate boundaries")
        if workflow_mode == "final_draft_audit" and item.get("action") in DESTRUCTIVE_ACTIONS:
            errors.append(prefix + " destructive actions are forbidden in final_draft_audit")
        if (
            completeness_status in {"partial", "unknown"}
            and item.get("action") in DESTRUCTIVE_ACTIONS
        ):
            if item.get("confidence") == "high":
                errors.append(
                    prefix + " cannot be high-confidence destructive while material completeness is not complete"
                )
            elif not flag_set & REVIEW_REQUIRED_FLAGS:
                warnings.append(
                    prefix + " should carry a review flag while material completeness is not complete"
                )
        if item.get("action") in DESTRUCTIVE_ACTIONS and not _nonempty_string(item.get("expected_join")):
            warnings.append(prefix + " changes continuity but has no expected_join")
        if domain_unresolved and item.get("domain_sensitive") and item.get("action") in DESTRUCTIVE_ACTIONS:
            if item.get("confidence") == "high":
                errors.append(prefix + " cannot be high-confidence while domain-sensitive context is unresolved")
            elif not flag_set & REVIEW_REQUIRED_FLAGS:
                warnings.append(prefix + " should carry needs_context or human_review")

    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "decision_count": len(decisions),
        "outline_unit_count": len((plan.get("outline") or {}).get("units", [])) if isinstance(plan.get("outline"), dict) else 0,
        "subtitle_alignment_status": alignment_phase_status,
        "workflow_mode": workflow_mode,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan")
    args = parser.parse_args()
    plan = json.loads(Path(args.plan).read_text(encoding="utf-8-sig"))
    result = validate(plan)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
