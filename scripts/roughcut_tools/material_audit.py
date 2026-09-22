"""Audit available rough-cut evidence without making editorial decisions."""

from __future__ import annotations

import json
import shutil
import subprocess
from functools import lru_cache
from pathlib import Path
from typing import Any

from .result import result

VALID_STATUSES = {"available", "partial", "missing", "unknown", "review"}


def _probe_media_uncached(path: Path) -> dict[str, Any]:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return {"path": str(path), "status": "unknown", "reason": "ffprobe unavailable"}
    completed = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries", "format=duration:stream=codec_type,width,height,r_frame_rate", "-of", "json", str(path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if completed.returncode != 0:
        return {"path": str(path), "status": "unknown", "reason": completed.stderr.strip() or "ffprobe failed"}
    try:
        data = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return {"path": str(path), "status": "unknown", "reason": "ffprobe returned invalid JSON"}
    raw_duration = (data.get("format") or {}).get("duration")
    try:
        duration_us = round(float(raw_duration) * 1_000_000)
    except (TypeError, ValueError):
        duration_us = 0
    if duration_us <= 0:
        return {"path": str(path), "status": "unknown", "reason": "media duration is missing or non-positive", "metadata": data}
    return {
        "path": str(path),
        "status": "available",
        "metadata": data,
        "duration_us": duration_us,
        "timebase": {"unit": "microseconds", "duration_us": duration_us},
    }


@lru_cache(maxsize=64)
def _probe_media_cached(path: str, mtime_ns: int, size: int) -> dict[str, Any]:
    """Cache one probe per unchanged file within a rough-cut process."""

    return _probe_media_uncached(Path(path))


def _probe_media(path: Path) -> dict[str, Any]:
    """Probe media once per unchanged path, preserving the public helper name."""

    try:
        resolved = path.resolve()
        stat = resolved.stat()
    except OSError:
        return _probe_media_uncached(path)
    return dict(_probe_media_cached(str(resolved), stat.st_mtime_ns, stat.st_size))


def _declared_duration_us(value: dict[str, Any]) -> int | None:
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


def _declared_media_evidence(kind: str, value: dict[str, Any]) -> dict[str, Any]:
    duration_us = _declared_duration_us(value)
    if duration_us is None:
        return {"kind": kind, "status": "unknown", "details": value, "reason": "media duration is missing or non-positive"}
    return {
        "kind": kind,
        "status": "available",
        "details": value,
        "duration_us": duration_us,
        "timebase": value.get("timebase") or {"unit": "microseconds", "duration_us": duration_us},
    }


def _evidence_for_value(kind: str, value: Any) -> tuple[dict[str, Any], str | None, str | None]:
    """Return evidence, a missing-key reason, and a hard input error."""
    if not value:
        return {"kind": kind, "status": "missing"}, kind, None
    if isinstance(value, dict):
        declared = value.get("status")
        path_value = value.get("path")
        if declared is not None and declared not in VALID_STATUSES:
            return {"kind": kind, "status": "unknown", "reason": f"invalid declared status {declared!r}"}, None, None
        if declared in {"missing", "unknown", "partial", "review"}:
            return {"kind": kind, "status": declared, "details": value}, kind, None
        if isinstance(path_value, str):
            path = Path(path_value)
            if not path.exists():
                return {"kind": kind, "status": "missing", "path": str(path)}, None, f"input path does not exist: {path}"
            if kind in {"video", "audio"}:
                return {"kind": kind, **_probe_media(path)}, None, None
            return {"kind": kind, "status": "available", "path": str(path), "timebase": {"unit": "microseconds"}}, None, None
        if declared == "available":
            if kind in {"video", "audio"}:
                evidence = _declared_media_evidence(kind, value)
                return evidence, kind if evidence.get("status") != "available" else None, None
            return {"kind": kind, "status": "available", "details": value, "timebase": value.get("timebase") or {"unit": "microseconds"}}, None, None
        if kind in {"video", "audio"} and ("duration_us" in value or "metadata" in value):
            evidence = _declared_media_evidence(kind, value)
            return evidence, kind if evidence.get("status") != "available" else None, None
        return {"kind": kind, "status": "unknown", "details": value, "reason": "no path or validated metadata"}, kind, None
    path = Path(str(value))
    if not path.exists():
        return {"kind": kind, "status": "missing", "path": str(path)}, None, f"input path does not exist: {path}"
    if kind in {"video", "audio"}:
        return {"kind": kind, **_probe_media(path)}, None, None
    return {"kind": kind, "status": "available", "path": str(path), "timebase": {"unit": "microseconds"}}, None, None


def audit_material_completeness(inputs: Any) -> dict[str, Any]:
    if not isinstance(inputs, dict):
        return result("material_completeness", input_errors=["inputs must be a JSON object"])
    checked: list[str] = []
    missing: list[str] = []
    evidence: list[dict[str, Any]] = []
    input_errors: list[str] = []
    uncertain: list[str] = []
    for key in ("video", "audio", "transcript", "subtitle_timing"):
        if key not in inputs or inputs.get(key) in (None, ""):
            missing.append(key)
            evidence.append({"kind": key, "status": "missing"})
            continue
        checked.append(key)
        item, missing_reason, hard_error = _evidence_for_value(key, inputs[key])
        evidence.append(item)
        if missing_reason:
            missing.append(key)
        if hard_error:
            input_errors.append(hard_error)
        if item.get("status") in {"unknown", "partial", "review"}:
            uncertain.append(key)
    status = "complete" if not missing and not uncertain and not input_errors else "partial" if checked else "unknown"
    errors = [] if status == "complete" and not input_errors else ["required evidence is missing, invalid, or uncertain; destructive decisions must be blocked"]
    return result(
        "material_completeness",
        data={"status": status, "checked": checked, "missing": missing, "uncertain": uncertain, "evidence": evidence, "impact": "none" if status == "complete" else "review_required"},
        errors=errors,
        input_errors=input_errors,
        warnings=["material completeness is partial or unknown"] if status != "complete" else [],
        summary={"status": status, "checked_count": len(checked), "missing_count": len(missing), "uncertain_count": len(uncertain)},
    )
