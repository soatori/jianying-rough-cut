"""Compare semantic order between rough-cut timelines."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from typing import Any

from .result import result


def _hash(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _sequence(value: Any, name: str) -> tuple[list[str], list[str]]:
    if isinstance(value, list):
        raw_sequence = value
        supplied_hash = None
    elif isinstance(value, dict):
        if isinstance(value.get("order"), list):
            raw_sequence = value["order"]
        elif isinstance(value.get("source_order" if name == "source" else "target_order"), list):
            raw_sequence = value["source_order" if name == "source" else "target_order"]
        elif isinstance(value.get("sequence"), list):
            raw_sequence = value["sequence"]
        else:
            return [], [f"{name}.order must be an array"]
        supplied_hash = value.get("source_order_hash" if name == "source" else "target_order_hash") or value.get("order_hash")
    else:
        return [], [f"{name}.order must be an array"]
    errors = []
    invalid_ids = []
    sequence = []
    for index, item in enumerate(raw_sequence):
        if not isinstance(item, str) or not item.strip():
            invalid_ids.append(index)
            continue
        sequence.append(item)
    if invalid_ids:
        errors.append(f"{name}.order contains invalid semantic IDs at indexes {invalid_ids}")
    if any(not item for item in sequence):
        errors.append(f"{name}.order contains an empty semantic ID")
    if len(sequence) != len(set(sequence)):
        errors.append(f"{name}.order contains duplicate semantic IDs")
    actual_hash = _hash(sequence)
    if supplied_hash is not None and supplied_hash != actual_hash:
        errors.append(f"{name}.order hash does not match the supplied sequence")
    return sequence, errors


def _mapping_list(value: Any) -> tuple[list[dict[str, str]], list[str]]:
    if value is None:
        return [], []
    if isinstance(value, dict):
        raw = [{"source": source, "target": target} for source, target in value.items()]
    elif isinstance(value, list):
        raw = value
    else:
        return [], ["semantic_mapping must be an array or legacy object"]
    mapping: list[dict[str, str]] = []
    errors: list[str] = []
    seen_sources: set[str] = set()
    seen_targets: set[str] = set()
    for index, item in enumerate(raw):
        if (
            not isinstance(item, dict)
            or not isinstance(item.get("source"), str)
            or not item.get("source").strip()
            or not isinstance(item.get("target"), str)
            or not item.get("target").strip()
        ):
            errors.append(f"semantic_mapping[{index}] must contain source and target")
            continue
        source, target = item["source"], item["target"]
        if source in seen_sources:
            errors.append(f"semantic_mapping duplicates source {source!r}")
        if target in seen_targets:
            errors.append(f"semantic_mapping duplicates target {target!r}")
        seen_sources.add(source)
        seen_targets.add(target)
        mapping.append({"source": source, "target": target})
    return mapping, errors


def compare_timeline_orders(source: Any, target: Any, semantic_mapping: Any = None) -> dict[str, Any]:
    source_order, errors = _sequence(source, "source")
    target_order, target_errors = _sequence(target, "target")
    errors.extend(target_errors)
    mapping, mapping_errors = _mapping_list(semantic_mapping)
    errors.extend(mapping_errors)
    source_set, target_set = set(source_order), set(target_order)
    mapping_sources = {item["source"] for item in mapping}
    mapping_targets = {item["target"] for item in mapping}
    if not errors:
        if source_order == target_order:
            status = "not_required"
        elif not mapping:
            status = "pending"
        elif not mapping_sources <= source_set or not mapping_targets <= target_set:
            errors.append("semantic_mapping contains an ID absent from source or target order")
            status = "blocked"
        elif source_set != target_set:
            # A deletion or append is not a complete one-to-one remap, even
            # when every shared unit has a mapping entry.
            status = "pending"
        elif mapping_sources != source_set & target_set or mapping_targets != source_set & target_set:
            status = "pending"
        else:
            status = "verified"
    else:
        status = "blocked"
    classifications = []
    for unit_id in sorted(source_set | target_set):
        if unit_id not in target_set:
            kind = "deleted"
        elif unit_id not in source_set:
            kind = "appended_media"
        elif source_order.index(unit_id) != target_order.index(unit_id):
            kind = "reordered"
        else:
            kind = "copied"
        classifications.append({"semantic_unit_id": unit_id, "kind": kind})
    warnings = []
    report_errors = list(errors)
    if status == "pending":
        message = "order mapping is incomplete; downstream alignment remains blocked"
        report_errors.append(message)
        warnings.append(message)
    data = {
        "source_order_hash": _hash(source_order),
        "target_order_hash": _hash(target_order),
        "source_sequence": source_order,
        "target_sequence": target_order,
        "remap_status": status,
        "semantic_mapping": mapping,
        "mapping": mapping,
        "changes": classifications,
    }
    return result("timeline_comparison", data=data, errors=report_errors, warnings=warnings, summary={"source_count": len(source_order), "target_count": len(target_order)})


def _stage_units(value: Any, name: str) -> tuple[list[dict[str, Any]], list[str]]:
    """Normalize a stage snapshot without assuming an application schema."""
    if isinstance(value, dict) and isinstance(value.get("units"), list):
        raw = value["units"]
    elif isinstance(value, list):
        raw = value
    elif isinstance(value, dict):
        sequence, errors = _sequence(value, name)
        return [{"id": item} for item in sequence], errors
    else:
        return [], [f"{name} must be an object, array, or object with units"]
    units: list[dict[str, Any]] = []
    errors: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(raw):
        if isinstance(item, str):
            unit = {"id": item}
        elif isinstance(item, dict):
            unit = dict(item)
        else:
            errors.append(f"{name}.units[{index}] must be an object or string")
            continue
        unit_id = unit.get("semantic_unit_id", unit.get("unit_id", unit.get("id")))
        if not isinstance(unit_id, str) or not unit_id.strip():
            errors.append(f"{name}.units[{index}] must contain a non-empty id")
            continue
        unit["id"] = unit_id
        if unit_id in seen:
            errors.append(f"{name}.units duplicates id {unit_id!r}")
        seen.add(unit_id)
        units.append(unit)
    return units, errors


def _unit_interval(unit: dict[str, Any]) -> tuple[int, int] | None:
    start = unit.get("start_us")
    end = unit.get("end_us")
    if isinstance(start, int) and not isinstance(start, bool) and isinstance(end, int) and not isinstance(end, bool):
        if 0 <= start <= end:
            return start, end
    timerange = unit.get("timerange")
    if isinstance(timerange, dict):
        start = timerange.get("start_us", timerange.get("start"))
        duration = timerange.get("duration_us", timerange.get("duration"))
        if isinstance(start, int) and isinstance(duration, int) and not isinstance(start, bool) and not isinstance(duration, bool) and start >= 0 and duration >= 0:
            return start, start + duration
    return None


def _unit_text(unit: dict[str, Any]) -> str | None:
    for key in ("text", "final_text", "visible_text", "display_text"):
        value = unit.get(key)
        if isinstance(value, str):
            return value
    return None


def _is_display_only(unit: dict[str, Any]) -> bool:
    return unit.get("display_only") is True or unit.get("text_authority") in {"packaging_display_text", "display_text"}


def _is_packaged(unit: dict[str, Any]) -> bool:
    if unit.get("packaged") is True:
        return True
    return any(unit.get(key) not in (None, [], {}, "") for key in ("visual", "visuals", "motion", "motion_event", "audio", "sound", "packaging"))


def _overlaps_exclusion(unit: dict[str, Any], exclusions: list[dict[str, Any]]) -> bool:
    interval = _unit_interval(unit)
    if interval is None:
        return False
    start, end = interval
    return any(
        isinstance(item, dict)
        and isinstance(item.get("start_us"), int)
        and isinstance(item.get("end_us"), int)
        and item["start_us"] < end
        and start < item["end_us"]
        for item in exclusions
    )


def build_stage_diff(
    source: Any,
    target: Any,
    semantic_mapping: Any = None,
    exclusions: Any = None,
) -> dict[str, Any]:
    """Compare two playback-ordered semantic snapshots.

    The function deliberately treats compound exclusions as annotations only:
    it never opens or invents units inside an excluded interval.
    """
    source_units, source_errors = _stage_units(source, "source")
    target_units, target_errors = _stage_units(target, "target")
    errors = source_errors + target_errors
    source_order = [unit["id"] for unit in source_units]
    target_order = [unit["id"] for unit in target_units]
    mapping, mapping_errors = _mapping_list(semantic_mapping)
    errors.extend(mapping_errors)
    source_by_id = {unit["id"]: unit for unit in source_units}
    target_by_id = {unit["id"]: unit for unit in target_units}
    source_set, target_set = set(source_order), set(target_order)
    if source_order == target_order:
        remap_status = "not_required"
        mapping = [{"source": unit_id, "target": unit_id} for unit_id in source_order]
    elif not mapping:
        remap_status = "pending"
        errors.append("stage order changed; semantic_mapping is required")
    elif not {item["source"] for item in mapping} <= source_set or not {item["target"] for item in mapping} <= target_set:
        remap_status = "blocked"
        errors.append("semantic_mapping contains an ID absent from source or target order")
    elif source_set != target_set:
        remap_status = "pending"
        errors.append("stage mapping does not cover additions or deletions as a one-to-one remap")
    elif {item["source"] for item in mapping} != source_set or {item["target"] for item in mapping} != target_set:
        remap_status = "pending"
        errors.append("stage mapping does not cover every semantic unit")
    else:
        remap_status = "verified"

    raw_exclusions = exclusions if isinstance(exclusions, list) else []
    normalized_exclusions: list[dict[str, Any]] = []
    for index, item in enumerate(raw_exclusions):
        if not isinstance(item, dict) or not isinstance(item.get("start_us"), int) or not isinstance(item.get("end_us"), int) or item["start_us"] < 0 or item["end_us"] <= item["start_us"]:
            errors.append(f"exclusions[{index}] must contain a valid start_us/end_us interval")
            continue
        normalized_exclusions.append({"start_us": item["start_us"], "end_us": item["end_us"], "reason": item.get("reason", "compound_exclusion")})

    changes: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()
    text_display_only = 0
    text_semantic_change = 0
    excluded_ids: list[str] = []
    for unit in source_units:
        source_id = unit["id"]
        target_id = next((item["target"] for item in mapping if item["source"] == source_id), source_id)
        target_unit = target_by_id.get(target_id)
        if target_unit is None:
            kind = "deleted"
            counts[kind] += 1
            changes.append({"source_id": source_id, "target_id": None, "kind": kind, "excluded": _overlaps_exclusion(unit, normalized_exclusions)})
            continue
        source_index = source_order.index(source_id)
        target_index = target_order.index(target_id)
        source_interval = _unit_interval(unit)
        target_interval = _unit_interval(target_unit)
        kinds: list[str] = []
        if source_index != target_index:
            kinds.append("reordered")
        if source_interval and target_interval and target_interval[1] - target_interval[0] < source_interval[1] - source_interval[0]:
            kinds.append("shortened")
        source_text = _unit_text(unit)
        target_text = _unit_text(target_unit)
        text_change = "unchanged"
        if source_text is not None and target_text is not None and source_text != target_text:
            if _is_display_only(target_unit):
                text_change = "display_only"
                text_display_only += 1
            else:
                text_change = "semantic_or_subtitle_change"
                text_semantic_change += 1
        if _is_packaged(target_unit) and not _is_packaged(unit):
            kinds.append("packaged")
        if not kinds:
            kinds.append("copied")
        primary_kind = next((kind for kind in ("deleted", "reordered", "shortened", "packaged", "copied") if kind in kinds), kinds[0])
        excluded = _overlaps_exclusion(unit, normalized_exclusions) or _overlaps_exclusion(target_unit, normalized_exclusions)
        if excluded:
            excluded_ids.append(source_id)
        counts[primary_kind] += 1
        changes.append({
            "source_id": source_id,
            "target_id": target_id,
            "kind": primary_kind,
            "kinds": kinds,
            "text_change": text_change,
            "source_text": source_text,
            "target_text": target_text,
            "source_index": source_index,
            "target_index": target_index,
            "excluded": excluded,
        })
    for unit in target_units:
        if unit["id"] not in target_set - source_set:
            counts["appended_media"] += 1
            changes.append({"source_id": None, "target_id": unit["id"], "kind": "appended_media", "excluded": _overlaps_exclusion(unit, normalized_exclusions)})

    report_errors = list(errors)
    if remap_status == "pending" and "stage order changed; semantic_mapping is required" not in report_errors:
        report_errors.append("stage order mapping is incomplete; downstream reuse remains blocked")
    data = {
        "source_order_hash": _hash(source_order),
        "target_order_hash": _hash(target_order),
        "source_sequence": source_order,
        "target_sequence": target_order,
        "semantic_mapping": mapping,
        "remap_status": remap_status,
        "changes": changes,
        "exclusions": normalized_exclusions,
        "excluded_unit_ids": excluded_ids,
        "text_change_policy": {
            "display_only": "reviewable packaging display change; does not replace final subtitle authority",
            "semantic_or_subtitle_change": "return to rough-cut/subtitle alignment review",
        },
    }
    return result(
        "stage_diff",
        data=data,
        errors=report_errors,
        warnings=["compound exclusion ranges are annotations; no nested content was analyzed"] if normalized_exclusions else [],
        summary={
            "source_count": len(source_units),
            "target_count": len(target_units),
            "change_count": len(changes),
            "display_only_text_changes": text_display_only,
            "semantic_or_subtitle_text_changes": text_semantic_change,
            "excluded_unit_count": len(excluded_ids),
            **{f"{key}_count": value for key, value in counts.items()},
        },
    )
