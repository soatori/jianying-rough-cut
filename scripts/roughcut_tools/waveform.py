"""Waveform-first evidence and subtitle-alignment candidates.

The module deliberately treats ASR word timing as a health check only.  A
boundary can be proposed from a detected audio pause, but it remains pending
until a human has listened through the edge.  Nothing here writes a Jianying
project or turns a candidate into an edit.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from .material_audit import _probe_media
from .result import result
from .validators.alignment_plan import validate_alignment_plan

DEFAULT_CONFIG: dict[str, Any] = {
    "noise_db": "-35dB",
    "pause_min_us": 120_000,
    "pause_cap_us": 350_000,
    "edge_window_us": 350_000,
    "tolerance_us": 40_000,
    "hop_us": 10_000,
    "window_us": 25_000,
    "auto_snap_within_tolerance": False,
}


def _hash(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _config(value: Any) -> tuple[dict[str, Any], list[str]]:
    config = dict(DEFAULT_CONFIG)
    if value is not None:
        if not isinstance(value, dict):
            return config, ["waveform config must be an object"]
        config.update(value)
    errors: list[str] = []
    for key in ("pause_min_us", "pause_cap_us", "edge_window_us", "tolerance_us", "hop_us", "window_us"):
        item = config.get(key)
        if not isinstance(item, int) or isinstance(item, bool) or item < 0:
            errors.append(f"waveform config {key} must be a non-negative integer")
    if (
        isinstance(config.get("pause_cap_us"), int)
        and not isinstance(config.get("pause_cap_us"), bool)
        and isinstance(config.get("pause_min_us"), int)
        and not isinstance(config.get("pause_min_us"), bool)
        and config["pause_cap_us"] < config["pause_min_us"]
    ):
        errors.append("waveform config pause_cap_us must be >= pause_min_us")
    if (
        isinstance(config.get("tolerance_us"), int)
        and not isinstance(config.get("tolerance_us"), bool)
        and isinstance(config.get("edge_window_us"), int)
        and not isinstance(config.get("edge_window_us"), bool)
        and config["tolerance_us"] > config["edge_window_us"]
    ):
        errors.append("waveform config tolerance_us must be <= edge_window_us")
    if isinstance(config.get("noise_db"), bool) or not isinstance(config.get("noise_db"), (str, int, float)):
        errors.append("waveform config noise_db must be a string or number")
    if not isinstance(config.get("auto_snap_within_tolerance"), bool):
        errors.append("waveform config auto_snap_within_tolerance must be boolean")
    if isinstance(config.get("noise_db"), (int, float)):
        config["noise_db"] = f"{config['noise_db']}dB"
    return config, errors


def _duration_us(value: dict[str, Any]) -> int | None:
    raw = value.get("duration_us")
    if isinstance(raw, int) and not isinstance(raw, bool) and raw > 0:
        return raw
    metadata = value.get("metadata")
    if isinstance(metadata, dict):
        raw = metadata.get("duration_us")
        if isinstance(raw, int) and not isinstance(raw, bool) and raw > 0:
            return raw
        raw = (metadata.get("format") or {}).get("duration")
        try:
            duration_us = round(float(raw) * 1_000_000)
        except (TypeError, ValueError):
            duration_us = 0
        if duration_us > 0:
            return duration_us
    return None


def _normalize_pauses(value: Any, minimum_us: int) -> tuple[list[dict[str, int]], list[str]]:
    if not isinstance(value, list):
        return [], ["waveform pause evidence must be an array"]
    pauses: list[dict[str, int]] = []
    errors: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            errors.append(f"waveform pauses[{index}] must be an object")
            continue
        start, end = item.get("start_us"), item.get("end_us")
        if (
            not isinstance(start, int)
            or isinstance(start, bool)
            or not isinstance(end, int)
            or isinstance(end, bool)
            or start < 0
            or end <= start
        ):
            errors.append(f"waveform pauses[{index}] has invalid microsecond boundaries")
            continue
        if end - start >= minimum_us:
            pauses.append({"start_us": start, "end_us": end})
    pauses.sort(key=lambda item: (item["start_us"], item["end_us"]))
    return pauses, errors


def _parse_silencedetect(stderr: str) -> list[dict[str, int]]:
    pauses: list[dict[str, int]] = []
    active_start: int | None = None
    for line in stderr.splitlines():
        start_match = re.search(r"silence_start:\s*([0-9.]+)", line)
        end_match = re.search(r"silence_end:\s*([0-9.]+)", line)
        if start_match:
            active_start = round(float(start_match.group(1)) * 1_000_000)
        if end_match and active_start is not None:
            end = round(float(end_match.group(1)) * 1_000_000)
            if end > active_start:
                pauses.append({"start_us": active_start, "end_us": end})
            active_start = None
    return pauses


def _detect_pauses(path: Path, config: dict[str, Any]) -> tuple[list[dict[str, int]], str | None]:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return [], "ffmpeg unavailable; provide precomputed waveform pause evidence"
    minimum_s = config["pause_min_us"] / 1_000_000
    completed = subprocess.run(
        [
            ffmpeg,
            "-hide_banner",
            "-nostdin",
            "-i",
            str(path),
            "-vn",
            "-af",
            f"silencedetect=noise={config['noise_db']}:d={minimum_s}",
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if completed.returncode != 0:
        return [], completed.stderr.strip() or "ffmpeg silencedetect failed"
    pauses, errors = _normalize_pauses(_parse_silencedetect(completed.stderr), config["pause_min_us"])
    return pauses, "; ".join(errors) if errors else None



def _file_sha256(path: Path) -> str | None:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError:
        return None
    return "sha256:" + digest.hexdigest()


AUDIO_IDENTITY_REQUIRED_FIELDS = {
    "content_hash", "duration_us", "sample_rate", "channels", "codec",
}


def _identity_complete(identity: dict[str, Any]) -> bool:
    if not AUDIO_IDENTITY_REQUIRED_FIELDS.issubset(identity):
        return False
    if not isinstance(identity.get("content_hash"), str) or not identity["content_hash"]:
        return False
    for field in ("duration_us", "sample_rate", "channels"):
        value = identity.get(field)
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            return False
    return isinstance(identity.get("codec"), str) and bool(identity["codec"])


def _audio_identity(
    path: Path | None,
    probed: dict[str, Any] | None = None,
    duration_us: int | None = None,
    supplied: dict[str, Any] | None = None,
) -> dict[str, Any]:
    identity: dict[str, Any] = {}
    explicit_identity = isinstance(supplied, dict) and bool(supplied)
    if explicit_identity:
        identity.update(supplied)
    if path is not None and path.is_file():
        content_hash = _file_sha256(path)
        if content_hash is not None:
            identity.setdefault("content_hash", content_hash)
    if duration_us is None and isinstance(probed, dict):
        raw_duration = probed.get("duration_us")
        if isinstance(raw_duration, int) and not isinstance(raw_duration, bool) and raw_duration > 0:
            duration_us = raw_duration
    if duration_us is not None:
        identity["duration_us"] = int(duration_us)
    metadata = (probed or {}).get("metadata")
    if isinstance(metadata, dict):
        for stream in metadata.get("streams") or []:
            if not isinstance(stream, dict) or stream.get("codec_type") != "audio":
                continue
            codec = stream.get("codec_name")
            if isinstance(codec, str) and codec:
                identity.setdefault("codec", codec)
            try:
                sample_rate = int(stream.get("sample_rate"))
            except (TypeError, ValueError):
                sample_rate = 0
            if sample_rate > 0:
                identity.setdefault("sample_rate", sample_rate)
            channels = stream.get("channels")
            if isinstance(channels, int) and not isinstance(channels, bool) and channels > 0:
                identity.setdefault("channels", channels)
            break
    if not explicit_identity and not _identity_complete(identity):
        return {}
    return identity


def extract_waveform_evidence(audio: Any, config: Any = None) -> dict[str, Any]:
    """Run one waveform pass, or normalize already computed evidence."""

    settings, config_errors = _config(config)
    if config_errors:
        return result("waveform_evidence", errors=config_errors)
    if isinstance(audio, dict) and "data" in audio and "report_type" in audio:
        if audio.get("ok") is False:
            return result("waveform_evidence", errors=["cannot consume blocked waveform evidence"])
        audio = audio.get("data")

    if isinstance(audio, dict) and isinstance(audio.get("waveform"), dict):
        nested = dict(audio["waveform"])
        nested.setdefault("duration_us", audio.get("duration_us"))
        nested.setdefault("metadata", audio.get("metadata"))
        nested.setdefault("path", audio.get("path"))
        audio = nested

    path: Path | None = None
    supplied: dict[str, Any] | None = None
    if isinstance(audio, dict):
        supplied = audio
        if isinstance(audio.get("path"), str):
            path = Path(audio["path"])
    elif isinstance(audio, (str, Path)):
        path = Path(audio)
    elif audio is None:
        return result("waveform_evidence", errors=["edited audio evidence is required"])
    else:
        return result("waveform_evidence", input_errors=["audio must be a media path or waveform evidence object"])

    probed: dict[str, Any] | None = None
    precomputed = supplied.get("pauses") if supplied is not None else None
    if precomputed is not None:
        pauses, pause_errors = _normalize_pauses(precomputed, settings["pause_min_us"])
        if pause_errors:
            return result("waveform_evidence", errors=pause_errors)
        duration = _duration_us(supplied or {})
        metadata = supplied.get("metadata") if supplied else None
        if duration is None and path is not None:
            if not path.exists():
                return result("waveform_evidence", input_errors=[f"audio path does not exist: {path}"])
            probed = _probe_media(path)
            duration = probed.get("duration_us") if probed.get("status") == "available" else None
            metadata = metadata or probed.get("metadata")
        if duration is None:
            return result("waveform_evidence", errors=["waveform evidence duration_us is required"])
        identity = _audio_identity(
            path,
            probed if duration is not None and path is not None else None,
            duration,
            supplied.get("identity") if supplied is not None else None,
        )
        data = {
            "status": "available",
            "path": str(path) if path is not None else supplied.get("path"),
            "duration_us": duration,
            "metadata": metadata,
            "identity": identity,
            "pauses": pauses,
            "config": settings,
            "method": "precomputed_waveform",
            "boundary_authority": "waveform",
        }
        return result("waveform_evidence", data=data, summary={"pause_count": len(pauses), "duration_us": duration})

    if path is None:
        return result("waveform_evidence", input_errors=["audio path or precomputed pauses are required"])
    if not path.exists():
        return result("waveform_evidence", input_errors=[f"audio path does not exist: {path}"])
    probed = _probe_media(path)
    if probed.get("status") != "available":
        return result("waveform_evidence", errors=[probed.get("reason", "audio probe failed")], data={"probe": probed})
    pauses, source_error = _detect_pauses(path, settings)
    if source_error:
        return result("waveform_evidence", errors=[source_error], data={"probe": probed})
    identity = _audio_identity(path, probed, probed["duration_us"])
    data = {
        "status": "available",
        "path": str(path),
        "duration_us": probed["duration_us"],
        "metadata": probed.get("metadata"),
        "identity": identity,
        "pauses": pauses,
        "config": settings,
        "method": "ffmpeg_silencedetect",
        "boundary_authority": "waveform",
    }
    return result("waveform_evidence", data=data, summary={"pause_count": len(pauses), "duration_us": probed["duration_us"]})


def _word_timing_health(subtitles: list[dict[str, Any]]) -> dict[str, str]:
    seen = False
    valid = True
    for subtitle in subtitles:
        if "words" not in subtitle:
            continue
        seen = True
        words = subtitle.get("words")
        if not isinstance(words, list) or not words:
            valid = False
            continue
        previous_end: float | int | None = None
        for word in words:
            if not isinstance(word, dict):
                valid = False
                continue
            start = word.get("start_us", word.get("start"))
            end = word.get("end_us", word.get("end"))
            if not isinstance(start, (int, float)) or isinstance(start, bool) or not isinstance(end, (int, float)) or isinstance(end, bool) or end <= start:
                valid = False
                continue
            if previous_end is not None and start < previous_end:
                valid = False
            previous_end = end
    return {"status": "valid" if seen and valid else "invalid" if seen else "unavailable", "role": "cross_check"}


def _find_pause_before(pauses: list[dict[str, int]], value: int, window: int) -> dict[str, Any] | None:
    matches: list[dict[str, Any]] = []
    for pause in pauses:
        if pause["start_us"] <= value <= pause["end_us"]:
            matches.append({"pause": pause, "candidate_us": pause["end_us"], "distance_us": 0})
        elif pause["end_us"] <= value and value - pause["end_us"] <= window:
            matches.append({"pause": pause, "candidate_us": pause["end_us"], "distance_us": value - pause["end_us"]})
    return min(matches, key=lambda item: (item["distance_us"], -item["pause"]["end_us"])) if matches else None


def _find_pause_after(pauses: list[dict[str, int]], value: int, window: int) -> dict[str, Any] | None:
    matches: list[dict[str, Any]] = []
    for pause in pauses:
        if pause["start_us"] <= value <= pause["end_us"]:
            matches.append({"pause": pause, "candidate_us": pause["start_us"], "distance_us": 0})
        elif pause["start_us"] >= value and pause["start_us"] - value <= window:
            matches.append({"pause": pause, "candidate_us": pause["start_us"], "distance_us": pause["start_us"] - value})
    return min(matches, key=lambda item: (item["distance_us"], item["pause"]["start_us"])) if matches else None


def _edge(value: int, candidate: dict[str, Any] | None, settings: dict[str, Any], label: str) -> dict[str, Any]:
    if candidate is None:
        return {
            "mode": "audio",
            "basis": "subtitle_boundary",
            "evidence": ["edited_audio", "current_subtitle_range"],
            "confidence": "low",
            "review": "pending",
            "previous_us": value,
            "selected_us": value,
            "candidate_us": None,
            "offset_us": 0,
            "selection": "retained_previous_for_listening",
            "reason": f"no isolated waveform pause near {label} boundary",
        }
    candidate_us = int(candidate["candidate_us"])
    offset = candidate_us - value
    snap = settings["auto_snap_within_tolerance"] and abs(offset) <= settings["tolerance_us"]
    return {
        "mode": "audio",
        "basis": "waveform",
        "evidence": ["edited_audio", "waveform"],
        "confidence": "high" if snap and abs(offset) <= settings["tolerance_us"] // 2 else "medium" if snap else "low",
        "review": "pending",
        "previous_us": value,
        "selected_us": candidate_us if snap else value,
        "candidate_us": candidate_us,
        "offset_us": offset,
        "selection": "waveform_snap" if snap else "waveform_candidate_only" if abs(offset) <= settings["tolerance_us"] else "retained_previous_for_listening",
        "pause": candidate["pause"],
        "reason": f"nearest waveform pause to {label} boundary",
    }


def _find_application_keys(value: Any, path: str, errors: list[str]) -> None:
    keys = {"draft_path", "timeline_id", "segment_id", "track_id", "material_id", "replica_path", "encryption"}
    if isinstance(value, dict):
        for key, item in value.items():
            if key in keys:
                errors.append(f"{path}.{key}: application-specific field is not allowed")
            _find_application_keys(item, f"{path}.{key}", errors)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _find_application_keys(item, f"{path}[{index}]", errors)


def build_waveform_alignment_plan(
    audio: Any,
    current_subtitles: Any,
    config: Any = None,
    *,
    text_authority: str = "current_visible_subtitle",
    subtitle_origin: str = "current_timeline",
    source_metadata: Any = None,
) -> dict[str, Any]:
    """Build a review-pending plan using waveform pauses as the boundary authority.

    ``current_subtitles`` can either be the saved subtitle units from an
    existing timeline or units generated from a timed transcript.  The
    boundary algorithm is shared; only the declared text source changes.
    """

    if not isinstance(current_subtitles, list) or not current_subtitles:
        return result("subtitle_alignment_plan", input_errors=["current_subtitles must be a non-empty list"])
    waveform_report = extract_waveform_evidence(audio, config)
    if not waveform_report["ok"]:
        return result(
            "subtitle_alignment_plan",
            data={"waveform_evidence": waveform_report.get("data")},
            errors=waveform_report.get("errors", []),
            input_errors=waveform_report.get("input_errors", []),
        )
    waveform = waveform_report["data"]
    settings = waveform["config"]
    errors: list[str] = []
    warnings: list[str] = []
    _find_application_keys(current_subtitles, "current_subtitles", errors)
    subtitles: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    seen_semantic_ids: set[str] = set()
    duration_us = waveform.get("duration_us")
    for index, raw in enumerate(current_subtitles):
        if not isinstance(raw, dict):
            errors.append(f"current_subtitles[{index}] must be an object")
            continue
        subtitle_id = str(raw.get("id", f"subtitle-{index + 1}"))
        semantic_id = str(raw.get("semantic_unit_id", subtitle_id))
        if subtitle_id in seen_ids:
            errors.append(f"current_subtitles duplicates id {subtitle_id!r}")
        if semantic_id in seen_semantic_ids:
            errors.append(f"current_subtitles duplicates semantic_unit_id {semantic_id!r}")
        seen_ids.add(subtitle_id)
        seen_semantic_ids.add(semantic_id)
        text = raw.get("text")
        start, end = raw.get("start_us"), raw.get("end_us")
        if not isinstance(text, str) or not text.strip():
            errors.append(f"current_subtitles[{index}].text must be non-empty")
            text = ""
        if not isinstance(start, int) or isinstance(start, bool) or start < 0:
            errors.append(f"current_subtitles[{index}].start_us must be a non-negative integer")
            start = 0
        if not isinstance(end, int) or isinstance(end, bool) or end <= start:
            errors.append(f"current_subtitles[{index}].end_us must be after start_us")
            end = start + 1
        if isinstance(duration_us, int) and end > duration_us:
            errors.append(f"current_subtitles[{index}].end_us exceeds waveform duration")
        subtitles.append({"raw": raw, "id": subtitle_id, "semantic_unit_id": semantic_id, "text": text, "start_us": start, "end_us": end})

    words_health = _word_timing_health([item["raw"] for item in subtitles])
    units: list[dict[str, Any]] = []
    for item in subtitles:
        raw = item["raw"]
        start_edge = _edge(item["start_us"], _find_pause_before(waveform["pauses"], item["start_us"], settings["edge_window_us"]), settings, "start")
        end_edge = _edge(item["end_us"], _find_pause_after(waveform["pauses"], item["end_us"], settings["edge_window_us"]), settings, "end")
        selected_start = start_edge["selected_us"]
        selected_end = end_edge["selected_us"]
        if selected_end <= selected_start:
            warnings.append(f"subtitle unit {item['semantic_unit_id']} retained its previous range because waveform candidates crossed")
            selected_start, selected_end = item["start_us"], item["end_us"]
            start_edge["selected_us"] = selected_start
            end_edge["selected_us"] = selected_end
            start_edge["selection"] = "retained_invalid_pair"
            end_edge["selection"] = "retained_invalid_pair"
        if start_edge["confidence"] == "low" or end_edge["confidence"] == "low":
            warnings.append(f"subtitle unit {item['semantic_unit_id']} requires listening at one or both edges")
        units.append({
            "id": item["id"],
            "semantic_unit_id": item["semantic_unit_id"],
            "text": item["text"],
            "start_us": selected_start,
            "end_us": selected_end,
            "previous_range": {"start_us": item["start_us"], "end_us": item["end_us"]},
            "evidence": {
                "previous_range": {"start_us": item["start_us"], "end_us": item["end_us"]},
                "start": start_edge,
                "end": end_edge,
                "word_timing_role": "cross_check_only",
            },
            "boundaries": {
                "start": {key: value for key, value in start_edge.items() if key not in {"selected_us", "previous_us"}},
                "end": {key: value for key, value in end_edge.items() if key not in {"selected_us", "previous_us"}},
            },
            "review_status": "pending",
            "corrections": raw.get("corrections", []) if isinstance(raw.get("corrections", []), list) else [],
        })

    subtitle_fingerprint = [
        {key: item[key] for key in ("id", "semantic_unit_id", "text", "start_us", "end_us")}
        for item in subtitles
    ]
    source_hash = _hash({"subtitle_units": subtitle_fingerprint, "audio_duration_us": duration_us})
    edited_audio_evidence = {
        "kind": "edited_audio",
        "status": "available",
        "method": waveform["method"],
    }
    if isinstance(waveform.get("identity"), dict) and waveform["identity"]:
        edited_audio_evidence["identity"] = dict(waveform["identity"])
    source = {
        "content_plan_id": "derived-waveform-alignment:" + source_hash.split(":", 1)[-1][:16],
        "content_plan_hash": source_hash,
        "timebase": "microseconds",
        "duration_us": duration_us,
        "evidence": [
            edited_audio_evidence,
            {"kind": "waveform", "status": "available", "method": waveform["method"], "pause_count": len(waveform["pauses"])},
        ],
        "text_authority": text_authority,
        "subtitle_origin": subtitle_origin,
    }
    if isinstance(source_metadata, dict):
        for key in ("segmentation_source", "text_source", "unresolved_terms", "correction_count", "generated_from"):
            if key in source_metadata:
                source[key] = source_metadata[key]

    plan = {
        "schema_version": 1,
        "plan_type": "subtitle_alignment_plan",
        "mode": "analysis",
        "source": source,
        "policy": {
            "mode": "hybrid",
            "default_boundary_mode": "audio",
            "boundary_authority": "waveform",
            "tolerance_us": settings["tolerance_us"],
            "detector": {
                "hop_us": settings["hop_us"],
                "window_us": settings["window_us"],
                "pause_min_us": settings["pause_min_us"],
                "pause_cap_us": settings["pause_cap_us"],
            },
            "words_health": words_health,
        },
        "subtitle_units": units,
        "review": {"status": "pending"},
        "recheck_if": [
            "rough-cut changes source order or duration",
            "the saved edited audio or manual subtitle segmentation changes",
            "the recording noise floor or waveform detector configuration changes",
        ],
        "notes": [
            "Waveform pauses locate candidates; each edge remains pending until human listening confirms the actual speech boundary.",
            "ASR word timing is a cross-check only and never controls start_us or end_us.",
            "Existing subtitle text is preserved when subtitle_origin=current_timeline; generated text comes only from the supplied timed transcript.",
            "This plan is application-independent and contains no Jianying write instructions.",
        ],
        "waveform_evidence": waveform,
    }
    validation = validate_alignment_plan(plan)
    errors.extend(validation.get("errors", []))
    warnings.extend(validation.get("warnings", []))
    if not waveform["pauses"]:
        warnings.append("no isolated waveform pauses were detected; all boundaries remain listening candidates")
    return result(
        "subtitle_alignment_plan",
        data=plan,
        errors=errors,
        warnings=warnings,
        summary={
            "subtitle_unit_count": len(units),
            "waveform_pause_count": len(waveform["pauses"]),
            "waveform_snapped_edge_count": sum(
                1
                for unit in units
                for edge in (unit["evidence"]["start"], unit["evidence"]["end"])
                if edge.get("selection") == "waveform_snap"
            ),
            "word_timing_status": words_health["status"],
        },
    )
