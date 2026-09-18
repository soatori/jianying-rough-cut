#!/usr/bin/env python3
"""Validate a generic, read-only Jianying final-draft analysis report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REPORT_TYPES = {"final_draft_audit", "timeline_comparison"}
TEXT_AUTHORITIES = {"final_visible_subtitle", "approved_subtitle_alignment"}
REVIEW_STATUSES = {"pending", "human_review", "approved", "not_required"}
REMAP_STATUSES = {"not_required", "pending", "verified", "blocked"}
SEMANTIC_ROLES = {
    "hook", "background", "question", "reaction", "answer", "evidence",
    "technical_detail", "contrast", "benefit", "summary", "cta",
}
APPLICATION_KEYS = {
    "draft_path", "timeline", "track_id", "track_type", "segment_id", "material_id",
    "asset_id", "replica_paths", "replica_manifest", "encryption", "json_path",
    "target_locator", "source_locator", "execution_handoff", "write_back", "apply",
}


def nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def string_list(path: str, value: Any, errors: list[str], *, required: bool = False) -> list[str]:
    if not isinstance(value, list):
        errors.append(f"{path}: must be an array of strings")
        return []
    result: list[str] = []
    for index, item in enumerate(value):
        if not nonempty(item):
            errors.append(f"{path}[{index}]: must be a non-empty string")
        else:
            result.append(item)
    if required and not result:
        errors.append(f"{path}: must contain at least one item")
    return result


def find_application_keys(value: Any, path: str, errors: list[str]) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key in APPLICATION_KEYS:
                errors.append(f"{path}.{key}: application-specific field is not allowed")
            find_application_keys(item, f"{path}.{key}", errors)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            find_application_keys(item, f"{path}[{index}]", errors)


def validate(report: Any) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(report, dict):
        return {"ok": False, "errors": ["report must be a JSON object"], "warnings": []}

    find_application_keys(report, "report", errors)
    if report.get("report_type") not in REPORT_TYPES:
        errors.append("report_type: unsupported report type")

    source = report.get("source")
    if not isinstance(source, dict):
        errors.append("source: required object")
        source = {}
    authority = source.get("text_authority")
    if authority not in TEXT_AUTHORITIES:
        errors.append("source.text_authority: must identify final subtitle authority")
    if report.get("report_type") == "final_draft_audit" and authority != "final_visible_subtitle":
        errors.append("final_draft_audit requires source.text_authority=final_visible_subtitle")
    reference = source.get("subtitle_reference")
    if not isinstance(reference, dict):
        errors.append("source.subtitle_reference: required object")
    else:
        for field in ("id", "hash"):
            if not nonempty(reference.get(field)):
                errors.append(f"source.subtitle_reference.{field}: required")
        if reference.get("status") not in {"stable", "approved"}:
            errors.append("source.subtitle_reference.status: must be stable or approved")
    string_list("source.evidence", source.get("evidence"), errors, required=True)

    evidence = report.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        errors.append("evidence: must be a non-empty array")
    else:
        for index, item in enumerate(evidence):
            path = f"evidence[{index}]"
            if not isinstance(item, dict) or not nonempty(item.get("kind")):
                errors.append(f"{path}: must contain kind")
            elif item.get("status") not in {"available", "partial", "missing", "review"}:
                errors.append(f"{path}.status: invalid")

    comparison = report.get("timeline_comparison")
    if not isinstance(comparison, dict):
        errors.append("timeline_comparison: required object")
        comparison = {}
    for field in ("source_order_hash", "target_order_hash"):
        if not nonempty(comparison.get(field)):
            errors.append(f"timeline_comparison.{field}: required")
    remap_status = comparison.get("remap_status")
    if remap_status not in REMAP_STATUSES:
        errors.append("timeline_comparison.remap_status: invalid")
    source_order = comparison.get("source_sequence")
    target_order = comparison.get("target_sequence")
    if not isinstance(source_order, list) or not isinstance(target_order, list):
        errors.append("timeline_comparison.source_sequence and target_sequence must be arrays")
    source_changed = source_order != target_order
    mapping = comparison.get("semantic_mapping", [])
    if not isinstance(mapping, list):
        errors.append("timeline_comparison.semantic_mapping: must be an array")
    elif source_changed and not mapping:
        errors.append("timeline_comparison.semantic_mapping: required when order changes")
    if source_changed and remap_status == "not_required":
        errors.append("timeline_comparison.remap_status cannot be not_required when order changes")

    groups = report.get("semantic_groups")
    if not isinstance(groups, list) or not groups:
        errors.append("semantic_groups: must be a non-empty array")
        groups = []
    group_ids: set[str] = set()
    for index, group in enumerate(groups):
        path = f"semantic_groups[{index}]"
        if not isinstance(group, dict):
            errors.append(f"{path}: must be an object")
            continue
        group_id = group.get("id")
        if not nonempty(group_id):
            errors.append(f"{path}.id: required")
        elif group_id in group_ids:
            errors.append(f"{path}.id: duplicated")
        else:
            group_ids.add(group_id)
        if not nonempty(group.get("semantic_unit_id")):
            errors.append(f"{path}.semantic_unit_id: required")
        if not nonempty(group.get("final_subtitle_text")):
            errors.append(f"{path}.final_subtitle_text: required")
        if group.get("role") not in SEMANTIC_ROLES:
            errors.append(f"{path}.role: unsupported semantic role")
        string_list(path + ".context_dependencies", group.get("context_dependencies"), errors)
        if not nonempty(group.get("speaker_id")) or not nonempty(group.get("speaker_function")):
            errors.append(f"{path}: speaker_id and speaker_function are required")
        if not nonempty(group.get("short_video_reason")):
            errors.append(f"{path}.short_video_reason: required")
        facts = group.get("protected_fact_flags")
        if not isinstance(facts, dict):
            errors.append(f"{path}.protected_fact_flags: required object")
        if not isinstance(group.get("needs_listen"), bool):
            errors.append(f"{path}.needs_listen: must be boolean")
        if group.get("needs_listen") and group.get("review_status") not in {"human_review", "pending"}:
            errors.append(f"{path}.review_status: listening-required group must be reviewable")
        if group.get("review_status") not in REVIEW_STATUSES:
            errors.append(f"{path}.review_status: invalid")

    protected = report.get("protected_facts")
    if not isinstance(protected, list):
        errors.append("protected_facts: must be an array")

    discrepancies = report.get("discrepancies")
    if not isinstance(discrepancies, list):
        errors.append("discrepancies: must be an array")
    else:
        for index, item in enumerate(discrepancies):
            path = f"discrepancies[{index}]"
            if not isinstance(item, dict):
                errors.append(f"{path}: must be an object")
                continue
            if not nonempty(item.get("type")) or not nonempty(item.get("summary")):
                errors.append(f"{path}: type and summary are required")
            if item.get("review_status") not in REVIEW_STATUSES:
                errors.append(f"{path}.review_status: invalid")
            if item.get("type") in {"subtitle_audio_mismatch", "asr_final_mismatch", "text_mismatch"} and item.get("review_status") != "human_review":
                errors.append(f"{path}: wording discrepancy must be human_review")

    review = report.get("review")
    if not isinstance(review, dict):
        errors.append("review: required object")
    else:
        if review.get("status") not in {"draft", "review", "approved"}:
            errors.append("review.status: invalid")
        string_list("review.flags", review.get("flags", []), errors)

    if report.get("report_type") == "final_draft_audit":
        forbidden = {"delete", "shorten", "reorder", "join", "write_back", "execution"}
        present = forbidden.intersection(report.keys())
        if present:
            errors.append(f"final_draft_audit: action fields are not allowed: {sorted(present)}")
        if remap_status == "blocked":
            warnings.append("timeline comparison is blocked; downstream packaging must stop")

    return {"ok": not errors, "errors": errors, "warnings": warnings, "semantic_group_count": len(groups)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report")
    args = parser.parse_args()
    try:
        report = json.loads(Path(args.report).read_text(encoding="utf-8-sig"))
        result = validate(report)
    except Exception as exc:  # pragma: no cover - defensive CLI boundary
        result = {"ok": False, "errors": [f"validation failed safely: {type(exc).__name__}: {exc}"], "warnings": []}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
