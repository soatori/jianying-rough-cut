"""Map source token times into an edited playback timeline."""

from __future__ import annotations

import hashlib
import json
import math
from itertools import pairwise
from typing import Any

from .result import result


def _hash(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _source_tokens(source_transcript: dict[str, Any]) -> list[dict[str, Any]]:
    source_tokens = source_transcript.get("tokens", [])
    if source_tokens:
        return [token for token in source_tokens if isinstance(token, dict)]
    tokens: list[dict[str, Any]] = []
    for unit in source_transcript.get("segments", source_transcript.get("units", [])) or []:
        if isinstance(unit, dict):
            for token in unit.get("tokens", []) or []:
                if isinstance(token, dict):
                    token_copy = dict(token)
                    token_copy.setdefault("semantic_unit_id", unit.get("semantic_unit_id", unit.get("id")))
                    tokens.append(token_copy)
    return tokens


def _validate_segments(edit_map: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    raw = edit_map.get("segments")
    if not isinstance(raw, list) or not raw:
        return [], [], ["edit_map.segments must be a non-empty array"]
    all_segments: list[dict[str, Any]] = []
    errors: list[str] = []
    for index, raw_segment in enumerate(raw):
        path = f"edit_map.segments[{index}]"
        if not isinstance(raw_segment, dict):
            errors.append(f"{path} must be an object")
            continue
        segment = dict(raw_segment)
        if segment.get("id") in (None, ""):
            errors.append(f"{path}.id is required")
        source_start = segment.get("source_start_us")
        source_end = segment.get("source_end_us")
        if not _is_int(source_start) or not _is_int(source_end) or source_start < 0 or source_end <= source_start:
            errors.append(f"{path}: source_start_us/source_end_us must be increasing integers")
            continue
        kept_value = segment.get("kept", True)
        if not isinstance(kept_value, bool):
            errors.append(f"{path}.kept must be boolean")
            continue
        kept = kept_value
        if kept:
            target_start = segment.get("target_start_us")
            target_end = segment.get("target_end_us")
            if not _is_int(target_start) or not _is_int(target_end) or target_start < 0 or target_end <= target_start:
                errors.append(f"{path}: kept segments require increasing target boundaries")
                continue
            speed = segment.get("speed", 1.0)
            if isinstance(speed, bool):
                errors.append(f"{path}.speed must be positive")
                continue
            try:
                speed_value = float(speed)
            except (TypeError, ValueError):
                speed_value = 0.0
            if not math.isfinite(speed_value) or speed_value <= 0:
                errors.append(f"{path}.speed must be positive")
                continue
            segment["speed"] = speed_value
        segment["kept"] = kept
        all_segments.append(segment)
    source_sorted = sorted(all_segments, key=lambda item: (item["source_start_us"], item["source_end_us"]))
    for previous, current in pairwise(source_sorted):
        if current["source_start_us"] < previous["source_end_us"]:
            errors.append("edit_map source segments overlap")
    kept_segments = sorted((item for item in all_segments if item["kept"]), key=lambda item: (item["target_start_us"], str(item.get("id", ""))))
    for previous, current in pairwise(kept_segments):
        if current["target_start_us"] < previous["target_end_us"]:
            errors.append("edit_map target segments overlap")
    return all_segments, kept_segments, errors


def _unit_texts(source_transcript: dict[str, Any]) -> dict[str, str]:
    values: dict[str, str] = {}
    for unit in source_transcript.get("segments", source_transcript.get("units", [])) or []:
        if isinstance(unit, dict):
            unit_id = unit.get("semantic_unit_id", unit.get("id"))
            if unit_id and isinstance(unit.get("text"), str):
                values[str(unit_id)] = unit["text"]
    return values


def build_playback_map(source_transcript: Any, edit_map: Any) -> dict[str, Any]:
    if not isinstance(source_transcript, dict) or not isinstance(edit_map, dict):
        return result("playback_map", input_errors=["source_transcript and edit_map must be JSON objects"])
    all_segments, kept_segments, errors = _validate_segments(edit_map)
    source_tokens = _source_tokens(source_transcript)
    if not source_tokens:
        errors.append("source transcript contains no tokens")
    mapped: list[dict[str, Any]] = []
    deleted_token_ids: list[str] = []
    unmapped: list[str] = []
    seen_token_ids: set[str] = set()
    for index, token in enumerate(source_tokens):
        raw_token_id = token.get("id")
        if raw_token_id in (None, ""):
            errors.append(f"source token {index}: id is required")
            continue
        token_id = str(raw_token_id)
        if token_id in seen_token_ids:
            unmapped.append(token_id)
            errors.append(f"source transcript duplicates token id {token_id!r}")
            continue
        seen_token_ids.add(token_id)
        start, end = token.get("start_us"), token.get("end_us")
        if not _is_int(start) or not _is_int(end) or start < 0 or end <= start:
            unmapped.append(token_id)
            errors.append(f"source token {token_id}: invalid source boundaries")
            continue
        matches = [
            segment
            for segment in all_segments
            if segment["source_start_us"] <= start and end <= segment["source_end_us"]
        ]
        if len(matches) > 1:
            unmapped.append(token_id)
            errors.append(f"source token {token_id}: multiple edit segments match")
            continue
        if not matches:
            overlapping = [
                segment
                for segment in all_segments
                if start < segment["source_end_us"] and segment["source_start_us"] < end
            ]
            unmapped.append(token_id)
            if overlapping:
                errors.append(f"source token {token_id}: crosses an edit segment boundary")
            else:
                errors.append(f"source token {token_id}: no kept or deleted edit segment covers it")
            continue
        segment = matches[0]
        if not segment["kept"]:
            deleted_token_ids.append(token_id)
            continue
        source_start = segment["source_start_us"]
        target_start = segment["target_start_us"]
        speed = segment["speed"]
        edited_start = target_start + round((start - source_start) / speed)
        edited_end = target_start + round((end - source_start) / speed)
        semantic_unit_id = token.get("semantic_unit_id", segment.get("semantic_unit_id"))
        if not semantic_unit_id:
            unmapped.append(token_id)
            errors.append(f"source token {token_id}: semantic_unit_id is required to build canonical units")
            continue
        mapped.append({
            **token,
            "id": token_id,
            "edited_start_us": edited_start,
            "edited_end_us": edited_end,
            "edit_segment_id": segment.get("id"),
            "semantic_unit_id": semantic_unit_id,
        })

    unit_texts = _unit_texts(source_transcript)
    units: list[dict[str, Any]] = []
    grouped: dict[str, list[dict[str, Any]]] = {}
    for token in mapped:
        unit_id = token.get("semantic_unit_id")
        if unit_id:
            grouped.setdefault(str(unit_id), []).append(token)
    for unit_id, tokens in grouped.items():
        tokens.sort(key=lambda item: (item["edited_start_us"], item["edited_end_us"], item["id"]))
        spans = [{"start_us": token["edited_start_us"], "end_us": token["edited_end_us"]} for token in tokens]
        units.append({
            "id": unit_id,
            "semantic_unit_id": unit_id,
            "text": unit_texts.get(unit_id, "".join(str(token.get("text", "")) for token in tokens)),
            "start_us": min(span["start_us"] for span in spans),
            "end_us": max(span["end_us"] for span in spans),
            "source_start_us": min(int(token["start_us"]) for token in tokens),
            "source_end_us": max(int(token["end_us"]) for token in tokens),
            "token_ids": [token["id"] for token in tokens],
            "spans": spans,
            "continuous": all(left["end_us"] == right["start_us"] for left, right in pairwise(spans)),
        })
    source_order: list[str] = []
    for token in source_tokens:
        unit_id = token.get("semantic_unit_id")
        if unit_id and str(unit_id) not in source_order:
            source_order.append(str(unit_id))
    target_order = [str(segment.get("semantic_unit_id")) for segment in kept_segments if segment.get("semantic_unit_id")]
    if not target_order:
        target_order = [unit["semantic_unit_id"] for unit in sorted(units, key=lambda item: item["start_us"])]
    target_order = list(dict.fromkeys(target_order))
    status = "blocked" if errors or unmapped else "verified"
    return result(
        "playback_map",
        data={
            "timebase": "microseconds",
            "tokens": mapped,
            "units": sorted(units, key=lambda item: (item["start_us"], item["id"])),
            "deleted_token_ids": deleted_token_ids,
            "unmapped_token_ids": unmapped,
            "source_order": source_order,
            "target_order": target_order,
            "source_order_hash": _hash(source_order),
            "target_order_hash": _hash(target_order),
            "order_hash": _hash(target_order),
            "duration_us": max((int(item["target_end_us"]) for item in kept_segments), default=0),
            "mapping_status": status,
            "content_plan_id": source_transcript.get("content_plan_id"),
            "content_plan_hash": source_transcript.get("content_plan_hash"),
            "evidence": source_transcript.get("evidence", [{"kind": "edited_audio", "status": "available"}]),
            "semantic_mapping": edit_map.get("semantic_mapping", source_transcript.get("semantic_mapping", [])),
        },
        errors=errors,
        warnings=["deleted source tokens are intentionally absent from playback"] if deleted_token_ids and not errors else [],
        summary={"mapped_token_count": len(mapped), "deleted_token_count": len(deleted_token_ids), "unmapped_token_count": len(unmapped), "unit_count": len(units)},
    )
