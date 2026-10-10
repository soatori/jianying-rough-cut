"""Validate read-only comparison inventory; never infer missing evidence."""

from __future__ import annotations

import math
from typing import Any

from ..result import result

ROLES = ("source", "rough cut", "intermediate edit stage", "manual fine cut", "reference")
RELATIONSHIPS = ("containment", "overlap", "deletion", "addition", "reorder")
INVENTORY = ("duration", "segment_count", *RELATIONSHIPS, "pause_evidence",
             "no_asr_spans", "protected_fact_exposure", "unresolved_term_exposure")
PURPOSES = ("content_completeness", "stage_delta", "preservation")
FORBIDDEN = {
    "fine_cut_direction", "cleanup_candidates", "proposed_changes", "instructions",
    "action", "actions", "edit_plan", "delete", "shorten", "join",
    "draft_path", "project_path", "timeline_path", "timeline", "track_id", "track_type",
    "segment_id", "material_id", "asset_id", "json_path", "target_locator", "source_locator",
    "replica_paths", "replica_manifest", "encryption", "execution_handoff", "write",
    "write_back", "write_back_instructions", "apply", "execution", "clone",
}


def nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def check_read_only(value: Any, path: str, errors: list[str]) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key in FORBIDDEN:
                errors.append(f"{path}.{key}: edit-planning/application field is forbidden")
            check_read_only(item, f"{path}.{key}", errors)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            check_read_only(item, f"{path}[{index}]", errors)


def check_finding(value: Any, path: str, field: str, in_scope: bool,
                  baseline_available: bool, errors: list[str], warnings: list[str]) -> None:
    if not isinstance(value, dict):
        errors.append(f"{path}: required evidence object")
        return
    status = value.get("status")
    allowed = ("available", "unavailable") if in_scope else ("not_assessed",)
    if status not in allowed:
        errors.append(f"{path}.status: must be one of {allowed}")
    verdict = value.get("verdict")
    if verdict not in ("PASS", "UNVERIFIED"):
        errors.append(f"{path}.verdict: must be PASS or UNVERIFIED")
    if field in RELATIONSHIPS and in_scope and not baseline_available and status != "unavailable":
        errors.append(f"{path}: baseline unavailable; relationship must be unavailable")
    if status != "available":
        if "value" in value or "evidence" in value:
            errors.append(f"{path}: unavailable/not_assessed must not contain fabricated value or evidence")
        if verdict != "UNVERIFIED":
            errors.append(f"{path}.verdict: missing evidence must remain UNVERIFIED")
        if status == "unavailable":
            warnings.append(f"{path}: required evidence unavailable")
        return
    evidence = value.get("evidence")
    if not isinstance(evidence, list) or not evidence or not all(nonempty(item) for item in evidence):
        errors.append(f"{path}.evidence: required non-empty array of evidence descriptions")
    observed = value.get("value")
    if field in ("duration", "segment_count"):
        number = (type(observed) in (int, float) and observed >= 0
                  and (type(observed) is int or math.isfinite(observed)))
        if not number or (field == "segment_count" and type(observed) is not int):
            errors.append(f"{path}.value: required finite nonnegative {'integer' if field == 'segment_count' else 'number in seconds'}")
    elif field in RELATIONSHIPS:
        if not nonempty(observed):
            errors.append(f"{path}.value: required relationship observation")
    else:
        if not isinstance(observed, list):
            errors.append(f"{path}.value: required array of observations (empty means observed none)")
        else:
            for index, row in enumerate(observed):
                if not isinstance(row, dict) or not nonempty(row.get("observation")):
                    errors.append(f"{path}.value[{index}]: required observation object")
                if field == "pause_evidence" and (not isinstance(row, dict) or not nonempty(row.get("functional_class"))):
                    errors.append(f"{path}.value[{index}].functional_class: required pause function")


def validate(report: Any) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    stages: list[Any] = []
    if not isinstance(report, dict):
        errors.append("report: must be a JSON object")
    else:
        check_read_only(report, "report", errors)
        if report.get("report_type") != "stage_comparison":
            errors.append("report_type: must be stage_comparison")
        purpose = report.get("purpose")
        if purpose not in PURPOSES:
            errors.append(f"purpose: must be one of {PURPOSES}")
        scope = report.get("scope")
        if not isinstance(scope, list) or not scope or not all(isinstance(field, str) and field in INVENTORY for field in scope):
            errors.append("scope: required non-empty array of inventory field names")
            scope = []
        elif len(set(scope)) != len(scope):
            errors.append("scope: duplicate field names")
        if not isinstance(report.get("stages"), list) or not report["stages"]:
            errors.append("stages: required non-empty array")
        else:
            stages = report["stages"]
        known: dict[str, dict[str, Any]] = {}
        for index, stage in enumerate(stages):
            path = f"stages[{index}]"
            if not isinstance(stage, dict):
                errors.append(f"{path}: required object")
                continue
            ref = stage.get("stage_ref")
            if not nonempty(ref):
                errors.append(f"{path}.stage_ref: required non-empty local reference")
            elif ref in known:
                errors.append(f"{path}.stage_ref: duplicate stage reference")
            else:
                known[ref] = stage
            if stage.get("role") not in ROLES:
                errors.append(f"{path}.role: invalid canonical stage role")
            if stage.get("authority") not in ("yes", "no", "unknown"):
                errors.append(f"{path}.authority: must be yes, no, or unknown")
        for index, stage in enumerate(stages):
            if not isinstance(stage, dict):
                continue
            path = f"stages[{index}]"
            baseline = stage.get("baseline")
            available = False
            if not isinstance(baseline, dict) or baseline.get("status") not in ("available", "unavailable"):
                errors.append(f"{path}.baseline: required available/unavailable baseline object")
            elif baseline["status"] == "unavailable":
                if "stage_ref" in baseline or "designation" in baseline:
                    errors.append(f"{path}.baseline: unavailable baseline must not identify an inferred stage")
                warnings.append(f"{path}.baseline: unavailable")
            else:
                ref = baseline.get("stage_ref")
                target = known.get(ref) if isinstance(ref, str) else None
                if target is None:
                    errors.append(f"{path}.baseline.stage_ref: must reference a supplied stage")
                designation = baseline.get("designation")
                if purpose == "content_completeness":
                    if designation != "source_role" or target is None or target.get("role") != "source":
                        errors.append(f"{path}.baseline: content completeness requires source_role baseline")
                elif designation != "user_designated":
                    errors.append(f"{path}.baseline.designation: explicit user_designated baseline required")
                if purpose == "preservation" and (target is None or target.get("role") != "manual fine cut" or target.get("authority") != "yes"):
                    errors.append(f"{path}.baseline: preservation requires the current authoritative manual fine cut")
                available = target is not None
            relationships = stage.get("relationships")
            if not isinstance(relationships, dict):
                errors.append(f"{path}.relationships: required object")
                relationships = {}
            for field in INVENTORY:
                container = relationships if field in RELATIONSHIPS else stage
                field_path = f"{path}.relationships.{field}" if field in RELATIONSHIPS else f"{path}.{field}"
                check_finding(container.get(field), field_path, field, field in scope,
                              available, errors, warnings)
    return result("stage_comparison_report_validation", errors=errors, warnings=warnings,
                  summary={"stage_count": len(stages)})
