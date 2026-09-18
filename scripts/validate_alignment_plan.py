#!/usr/bin/env python3
"""Validate an application-independent subtitle alignment plan."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


MODES = {"audio", "picture", "manual"}
BASES = {
    "word_boundary", "phrase_boundary", "pause", "waveform", "shot_boundary",
    "speaker_change", "manual_marker", "subtitle_boundary",
}
CONFIDENCE = {"high", "medium", "low"}
PLAN_STATUS = {"draft", "stable", "approved"}
REVIEW_STATUS = {"pending", "approved", "not_required"}
WORDS_STATUS = {"valid", "invalid", "unavailable"}
WORDS_ROLE = {"cross_check", "fallback"}
REMAP_STATUSES = {"not_required", "pending", "verified", "blocked"}

# These keys belong to the Jianying adapter, never to a generic editorial plan.
APPLICATION_KEYS = {
    "draft_path", "timeline", "track_id", "track_type", "segment_id", "material_id",
    "replica_paths", "replica_manifest", "encryption", "json_path", "keep_blocks",
    "execution_handoff", "target_locator", "source_locator", "content_path",
}


def is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


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


def validate_boundary(path: str, value: Any, errors: list[str]) -> tuple[str | None, str | None, str | None]:
    if not isinstance(value, dict):
        errors.append(f"{path}: required object")
        return None, None, None
    mode = value.get("mode")
    basis = value.get("basis")
    review = value.get("review", "pending")
    if mode not in MODES:
        errors.append(f"{path}.mode: must be audio, picture, or manual")
        mode = None
    if basis not in BASES:
        errors.append(f"{path}.basis: unsupported boundary basis")
        basis = None
    if review not in REVIEW_STATUS:
        errors.append(f"{path}.review: invalid review status")
        review = None
    string_list(f"{path}.evidence", value.get("evidence"), errors, required=True)
    confidence = value.get("confidence")
    if confidence not in CONFIDENCE:
        errors.append(f"{path}.confidence: invalid confidence")
        confidence = None
    if mode == "picture" and basis not in {"shot_boundary", "speaker_change", "manual_marker"}:
        errors.append(f"{path}: picture mode requires a shot, speaker, or manual basis")
    if mode == "manual" and review != "approved":
        errors.append(f"{path}: manual boundary requires review=approved")
    if confidence == "low" and review == "not_required":
        errors.append(f"{path}: low-confidence boundary cannot be not_required")
    return mode, confidence, review


def validate(plan: Any) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(plan, dict):
        return {"ok": False, "errors": ["plan must be a JSON object"], "warnings": []}

    if plan.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    if plan.get("plan_type") != "subtitle_alignment_plan":
        errors.append("plan_type must be subtitle_alignment_plan")
    find_application_keys(plan, "plan", errors)

    source = plan.get("source")
    duration_us: int | None = None
    if not isinstance(source, dict):
        errors.append("source must be an object")
        source = {}
    else:
        for field in ("content_plan_id", "content_plan_hash"):
            if not nonempty(source.get(field)):
                errors.append(f"source.{field} is required")
        if source.get("timebase") != "microseconds":
            errors.append("source.timebase must be microseconds")
        if "text_authority" in source and source.get("text_authority") not in {
            "final_visible_subtitle", "approved_subtitle_alignment", "edited_timeline_audio"
        }:
            errors.append("source.text_authority is invalid")
        duration_us = source.get("duration_us")
        if not is_int(duration_us) or duration_us <= 0:
            errors.append("source.duration_us must be a positive integer")
            duration_us = None
        evidence = source.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            errors.append("source.evidence must be a non-empty array")
        else:
            kinds: set[str] = set()
            for index, item in enumerate(evidence):
                if not isinstance(item, dict) or not nonempty(item.get("kind")):
                    errors.append(f"source.evidence[{index}] must contain kind")
                elif isinstance(item.get("kind"), str):
                    kinds.add(item["kind"])
            if not kinds & {"edited_audio", "waveform"}:
                errors.append("source.evidence must include edited_audio or waveform evidence")

    if plan.get("mode") == "final_draft_audit":
        if source.get("text_authority") != "final_visible_subtitle":
            errors.append("final_draft_audit alignment requires source.text_authority=final_visible_subtitle")
        subtitle_reference = source.get("subtitle_reference")
        if not isinstance(subtitle_reference, dict):
            errors.append("final_draft_audit alignment requires source.subtitle_reference")
        else:
            for field in ("id", "hash"):
                if not nonempty(subtitle_reference.get(field)):
                    errors.append(f"source.subtitle_reference.{field} is required")

    comparison = plan.get("comparison")
    if comparison is not None:
        if not isinstance(comparison, dict):
            errors.append("comparison must be an object")
        else:
            for field in ("source_order_hash", "target_order_hash"):
                if not nonempty(comparison.get(field)):
                    errors.append(f"comparison.{field} is required")
            remap_status = comparison.get("remap_status")
            if remap_status not in REMAP_STATUSES:
                errors.append("comparison.remap_status is invalid")
            source_sequence = comparison.get("source_sequence")
            target_sequence = comparison.get("target_sequence")
            if not isinstance(source_sequence, list) or not isinstance(target_sequence, list):
                errors.append("comparison source_sequence and target_sequence must be arrays")
            elif source_sequence != target_sequence:
                mapping = comparison.get("semantic_mapping")
                if not isinstance(mapping, list) or not mapping:
                    errors.append("comparison.semantic_mapping is required when order changes")
                if remap_status == "not_required":
                    errors.append("comparison.remap_status cannot be not_required when order changes")
            if isinstance(plan.get("review"), dict) and plan["review"].get("status") == "approved" and remap_status not in {"not_required", "verified"}:
                errors.append("approved alignment requires comparison.remap_status=not_required or verified")

    policy = plan.get("policy")
    if not isinstance(policy, dict):
        errors.append("policy must be an object")
    else:
        if policy.get("mode") != "hybrid":
            errors.append("policy.mode must be hybrid")
        if policy.get("default_boundary_mode", "audio") != "audio":
            errors.append("policy.default_boundary_mode must be audio")
        tolerance = policy.get("tolerance_us", 40_000)
        if not is_int(tolerance) or not 0 < tolerance <= 500_000:
            errors.append("policy.tolerance_us must be between 1 and 500000")
        detector = policy.get("detector", {})
        if not isinstance(detector, dict):
            errors.append("policy.detector must be an object")
        else:
            for field in ("hop_us", "window_us", "pause_min_us", "pause_cap_us"):
                value = detector.get(field)
                if not is_int(value) or value < 0:
                    errors.append(f"policy.detector.{field} must be a non-negative integer")
            if (
                is_int(detector.get("pause_min_us"))
                and is_int(detector.get("pause_cap_us"))
                and detector["pause_cap_us"] < detector["pause_min_us"]
            ):
                errors.append("policy.detector.pause_cap_us must be >= pause_min_us")

        words = policy.get("words_health")
        if not isinstance(words, dict):
            errors.append("policy.words_health must be an object")
        else:
            if words.get("status") not in WORDS_STATUS:
                errors.append("policy.words_health.status is invalid")
            if words.get("role") not in WORDS_ROLE:
                errors.append("policy.words_health.role must be cross_check or fallback")
            if words.get("status") == "valid" and words.get("role") != "cross_check":
                errors.append("valid word timing may only be used as cross_check evidence")

    units = plan.get("subtitle_units")
    if not isinstance(units, list) or not units:
        errors.append("subtitle_units must be a non-empty array")
        units = []
    unit_ids: set[str] = set()
    for index, unit in enumerate(units):
        path = f"subtitle_units[{index}]"
        if not isinstance(unit, dict):
            errors.append(f"{path} must be an object")
            continue
        unit_id = unit.get("id")
        if not nonempty(unit_id):
            errors.append(f"{path}.id is required")
        elif unit_id in unit_ids:
            errors.append(f"{path}.id is duplicated")
        else:
            unit_ids.add(unit_id)
        if not nonempty(unit.get("semantic_unit_id")):
            errors.append(f"{path}.semantic_unit_id is required")
        if not nonempty(unit.get("text")):
            errors.append(f"{path}.text is required")
        start = unit.get("start_us")
        end = unit.get("end_us")
        if not is_int(start) or start < 0:
            errors.append(f"{path}.start_us must be a non-negative integer")
        if not is_int(end) or end <= (start if is_int(start) else 0):
            errors.append(f"{path}.end_us must be after start_us")
        if duration_us is not None and is_int(end) and end > duration_us:
            errors.append(f"{path}.end_us exceeds source.duration_us")
        boundaries = unit.get("boundaries")
        if not isinstance(boundaries, dict):
            errors.append(f"{path}.boundaries must be an object")
        else:
            validate_boundary(f"{path}.boundaries.start", boundaries.get("start"), errors)
            validate_boundary(f"{path}.boundaries.end", boundaries.get("end"), errors)
        review = unit.get("review_status", "pending")
        if review not in REVIEW_STATUS:
            errors.append(f"{path}.review_status is invalid")
        corrections = unit.get("corrections", [])
        if not isinstance(corrections, list):
            errors.append(f"{path}.corrections must be an array")
        else:
            for cindex, correction in enumerate(corrections):
                if not isinstance(correction, dict) or not nonempty(correction.get("kind")):
                    errors.append(f"{path}.corrections[{cindex}] must contain kind")
                elif not nonempty(correction.get("reason")):
                    errors.append(f"{path}.corrections[{cindex}].reason is required")

    review = plan.get("review")
    if not isinstance(review, dict):
        errors.append("review must be an object")
    else:
        status = review.get("status")
        if status not in PLAN_STATUS:
            errors.append("review.status is invalid")
        if status == "approved":
            for index, unit in enumerate(units):
                if isinstance(unit, dict) and unit.get("review_status", "pending") != "approved":
                    errors.append(f"subtitle_units[{index}] must be approved before plan approval")

    string_list("recheck_if", plan.get("recheck_if"), errors, required=True)
    if plan.get("notes") is not None and not isinstance(plan.get("notes"), list):
        errors.append("notes must be an array when present")

    review_obj = plan.get("review") if isinstance(plan.get("review"), dict) else {}
    if review_obj.get("status") == "approved":
        def _has_manual_mode(boundaries: object) -> bool:
            if not isinstance(boundaries, dict):
                return False
            for end in ("start", "end"):
                edge = boundaries.get(end)
                if isinstance(edge, dict) and edge.get("mode") == "manual":
                    return True
            return False

        if any(_has_manual_mode(unit.get("boundaries")) for unit in units if isinstance(unit, dict)):
            warnings.append("approved plan contains manually resolved boundaries; retain the evidence for audit")

    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "subtitle_unit_count": len(units),
    }


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: validate_alignment_plan.py <plan.json>", file=sys.stderr)
        return 2
    try:
        data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8-sig"))
        result = validate(data)
    except Exception as exc:
        result = {"ok": False, "errors": [f"validation failed safely: {type(exc).__name__}: {exc}"], "warnings": []}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
