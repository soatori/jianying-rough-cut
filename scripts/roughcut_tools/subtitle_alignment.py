"""Build application-independent subtitle alignment candidates."""

from __future__ import annotations

import hashlib
import json
from itertools import pairwise
from typing import Any

from .result import result
from .validators.alignment_plan import validate_alignment_plan

APPLICATION_KEYS = {"draft_path", "timeline_id", "segment_id", "track_id", "material_id", "replica_path", "encryption"}


def _hash(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _payload(value: Any) -> Any:
    if isinstance(value, dict) and "data" in value and "report_type" in value:
        if value.get("ok") is False:
            raise ValueError("cannot build alignment from a blocked playback-map report")
        return value.get("data")
    return value


def _mapping_list(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        return [{"source": source, "target": target} for source, target in value.items()]
    return []


def build_subtitle_alignment_plan(playback_map: Any, current_subtitles: Any) -> dict[str, Any]:
    try:
        playback_map = _payload(playback_map)
    except ValueError as exc:
        return result("subtitle_alignment_plan", errors=[str(exc)])
    if not isinstance(playback_map, dict) or not isinstance(current_subtitles, list):
        return result("subtitle_alignment_plan", input_errors=["playback_map must be an object and current_subtitles must be a list"])
    errors: list[str] = []
    for key in APPLICATION_KEYS:
        if key in playback_map:
            errors.append(f"application-specific key is not allowed: {key}")
    mapped = playback_map.get("tokens")
    if not isinstance(mapped, list):
        return result("subtitle_alignment_plan", errors=errors + ["playback_map.tokens is required for token-based alignment"])
    if playback_map.get("mapping_status") != "verified":
        errors.append(f"playback mapping status is {playback_map.get('mapping_status')!r}; alignment is blocked")
    if playback_map.get("unmapped_token_ids"):
        errors.append("playback map contains unmapped tokens")
    duration_us = playback_map.get("duration_us")
    if not isinstance(duration_us, int) or duration_us <= 0:
        errors.append("playback_map.duration_us must be a positive integer")
        duration_us = None
    playback_units = playback_map.get("units")
    if not isinstance(playback_units, list) or not playback_units:
        errors.append("playback_map.units is required for semantic alignment")
        playback_units = []
    playback_unit_ids: set[str] = set()
    for index, playback_unit in enumerate(playback_units):
        if not isinstance(playback_unit, dict) or not playback_unit.get("semantic_unit_id"):
            errors.append(f"playback_map.units[{index}] must contain semantic_unit_id")
            continue
        unit_id = str(playback_unit["semantic_unit_id"])
        if unit_id in playback_unit_ids:
            errors.append(f"playback_map.units duplicates semantic_unit_id {unit_id!r}")
        playback_unit_ids.add(unit_id)
        if playback_unit.get("continuous") is False:
            errors.append(f"playback unit {unit_id} has a non-contiguous edited interval")
    token_by_unit: dict[str, list[dict[str, Any]]] = {}
    token_ids: set[str] = set()
    for index, token in enumerate(mapped):
        if not isinstance(token, dict):
            errors.append(f"playback_map.tokens[{index}] must be an object")
            continue
        token_id = str(token.get("id", f"token-{index + 1}"))
        if token_id in token_ids:
            errors.append(f"playback_map.tokens duplicates id {token_id!r}")
        token_ids.add(token_id)
        semantic_id = token.get("semantic_unit_id")
        start, end = token.get("edited_start_us"), token.get("edited_end_us")
        if not semantic_id or not isinstance(start, int) or isinstance(start, bool) or not isinstance(end, int) or isinstance(end, bool) or start < 0 or end <= start:
            errors.append(f"playback_map token {token_id} has no resolvable edited boundary or semantic_unit_id")
            continue
        token_by_unit.setdefault(str(semantic_id), []).append(token)
    units: list[dict[str, Any]] = []
    unit_ids: set[str] = set()
    semantic_ids: set[str] = set()
    for index, subtitle in enumerate(current_subtitles):
        if not isinstance(subtitle, dict):
            errors.append(f"current_subtitles[{index}] must be an object")
            continue
        semantic_id = subtitle.get("semantic_unit_id", subtitle.get("id", f"subtitle-{index + 1}"))
        semantic_id = str(semantic_id)
        unit_id = str(subtitle.get("id", f"subtitle-{index + 1}"))
        if unit_id in unit_ids:
            errors.append(f"current_subtitles duplicates id {unit_id!r}")
        unit_ids.add(unit_id)
        if semantic_id in semantic_ids:
            errors.append(f"current_subtitles duplicates semantic_unit_id {semantic_id!r}")
        semantic_ids.add(semantic_id)
        if playback_unit_ids and semantic_id not in playback_unit_ids:
            errors.append(f"subtitle unit {semantic_id} is absent from playback_map.units")
        matches = token_by_unit.get(semantic_id, [])
        if not matches:
            errors.append(f"subtitle unit {semantic_id} has no token mapping")
            continue
        original_matches = list(matches)
        if any(left["edited_start_us"] > right["edited_start_us"] for left, right in pairwise(original_matches)):
            errors.append(f"subtitle unit {semantic_id} has non-monotonic mapped tokens")
        if any(left["edited_end_us"] != right["edited_start_us"] for left, right in pairwise(original_matches)):
            errors.append(f"subtitle unit {semantic_id} has non-contiguous edited token intervals")
        matches = sorted(original_matches, key=lambda item: (item["edited_start_us"], item["edited_end_us"], str(item.get("id"))))
        segment_ids = {str(item.get("edit_segment_id")) for item in matches if item.get("edit_segment_id") is not None}
        if len(segment_ids) > 1:
            errors.append(f"subtitle unit {semantic_id} spans multiple edit segments and needs manual remap")
        start = min(item["edited_start_us"] for item in matches)
        end = max(item["edited_end_us"] for item in matches)
        text = subtitle.get("text")
        if not isinstance(text, str) or not text:
            errors.append(f"subtitle unit {semantic_id} requires non-empty text")
            text = ""
        boundary = {
            "mode": "audio",
            "basis": "word_boundary",
            "evidence": ["edited_audio", "token_mapping"],
            "confidence": "medium",
            "review": "pending",
        }
        units.append({
            "id": unit_id,
            "semantic_unit_id": semantic_id,
            "text": text,
            "start_us": start,
            "end_us": end,
            "previous_range": {
                "start_us": subtitle.get("start_us"),
                "end_us": subtitle.get("end_us"),
            } if isinstance(subtitle.get("start_us"), int) and isinstance(subtitle.get("end_us"), int) else None,
            "evidence": {
                "token_mapping": [
                    {
                        "token_id": item.get("id"),
                        "edited_start_us": item.get("edited_start_us"),
                        "edited_end_us": item.get("edited_end_us"),
                        "source_start_us": item.get("start_us"),
                        "source_end_us": item.get("end_us"),
                    }
                    for item in matches
                ],
                "previous_range": {
                    "start_us": subtitle.get("start_us"),
                    "end_us": subtitle.get("end_us"),
                } if isinstance(subtitle.get("start_us"), int) and isinstance(subtitle.get("end_us"), int) else None,
            },
            "boundaries": {"start": dict(boundary), "end": dict(boundary)},
            "review_status": "pending",
            "corrections": subtitle.get("corrections", []) if isinstance(subtitle.get("corrections", []), list) else [],
        })

    source_hash = playback_map.get("content_plan_hash")
    if not isinstance(source_hash, str) or not source_hash:
        source_hash = _hash({"tokens": [{key: token.get(key) for key in ("id", "start_us", "end_us", "semantic_unit_id")} for token in mapped if isinstance(token, dict)]})
    content_plan_id = playback_map.get("content_plan_id")
    if not isinstance(content_plan_id, str) or not content_plan_id:
        content_plan_id = "derived-content-plan:" + source_hash.split(":", 1)[-1][:16]
    evidence = playback_map.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        errors.append("playback_map.evidence is required")
        evidence = []
    normalized_evidence: list[dict[str, Any]] = []
    for item in evidence:
        if isinstance(item, dict) and item.get("kind"):
            normalized_evidence.append(dict(item))
        elif isinstance(item, str) and item:
            normalized_evidence.append({"kind": "edited_audio", "status": "available", "source": item})
    if not normalized_evidence:
        errors.append("playback_map.evidence must contain usable evidence")
        normalized_evidence = [{"kind": "edited_audio", "status": "available", "source": "token_mapping"}]
    elif not any(item.get("kind") in {"edited_audio", "waveform"} for item in normalized_evidence):
        normalized_evidence.insert(0, {"kind": "edited_audio", "status": "available", "source": "token_mapping"})
    policy = {
        "mode": "hybrid",
        "default_boundary_mode": "audio",
        "tolerance_us": 40_000,
        "detector": {
            "hop_us": 10_000,
            "window_us": 25_000,
            "pause_min_us": 120_000,
            "pause_cap_us": 350_000,
        },
        "words_health": playback_map.get("words_health", {"status": "unavailable", "role": "fallback"}),
    }
    source_order = playback_map.get("source_order", [])
    target_order = playback_map.get("target_order", [])
    comparison = None
    if isinstance(source_order, list) and isinstance(target_order, list):
        source_hash_value = playback_map.get("source_order_hash") or _hash(source_order)
        target_hash_value = playback_map.get("target_order_hash") or _hash(target_order)
        mapping = _mapping_list(playback_map.get("semantic_mapping"))
        comparison = {
            "source_order_hash": source_hash_value,
            "target_order_hash": target_hash_value,
            "source_sequence": source_order,
            "target_sequence": target_order,
            "remap_status": "not_required" if source_order == target_order else playback_map.get("remap_status", "pending"),
            "semantic_mapping": mapping,
        }
    else:
        errors.append("playback_map.source_order and target_order must be arrays")
    plan = {
        "schema_version": 1,
        "plan_type": "subtitle_alignment_plan",
        "mode": "analysis",
        "source": {
            "content_plan_id": content_plan_id,
            "content_plan_hash": source_hash,
            "timebase": "microseconds",
            "duration_us": duration_us,
            "evidence": normalized_evidence,
            "text_authority": "current_visible_subtitle",
            "subtitle_origin": "current_timeline",
            "playback_order_hash": playback_map.get("target_order_hash", playback_map.get("order_hash")),
        },
        "policy": policy,
        "subtitle_units": units,
        "review": {"status": "pending"},
        "recheck_if": ["rough-cut changes source order or duration"],
    }
    if comparison is not None:
        plan["comparison"] = comparison
    validation = validate_alignment_plan(plan)
    errors.extend(validation.get("errors", []))
    return result("subtitle_alignment_plan", data=plan, errors=errors, warnings=["all generated boundaries require review", *validation.get("warnings", [])] if units else validation.get("warnings", []), summary={"subtitle_unit_count": len(units)})
