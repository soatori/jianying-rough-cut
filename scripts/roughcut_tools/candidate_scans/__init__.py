"""Conservative Pass 2 candidate detectors.

These functions locate review candidates. They never authorize deletion.
"""

from __future__ import annotations

import difflib
import re
import shutil
import subprocess
from itertools import pairwise
from pathlib import Path
from typing import Any

from ..result import result

PAUSE_FUNCTIONS = (
    "hesitation", "sentence_boundary", "speaker_handoff", "topic_shift",
    "emphasis", "emotional_beat", "breath", "failed_take_gap", "edit_damage",
)


def _units(playback: Any) -> list[dict[str, Any]] | None:
    if isinstance(playback, dict):
        if "units" in playback:
            value = playback.get("units")
        elif "segments" in playback:
            value = playback.get("segments")
        else:
            return None
        if not isinstance(value, list) or not value:
            return None
        normalized = [item for item in value if isinstance(item, dict)]
        if len(normalized) != len(value):
            return None
        for item in normalized:
            start = item.get("start_us", item.get("edited_start_us"))
            end = item.get("end_us", item.get("edited_end_us"))
            if not item.get("id") or not isinstance(start, int) or isinstance(start, bool) or not isinstance(end, int) or isinstance(end, bool) or end <= start:
                return None
        return normalized
    if isinstance(playback, list):
        return [item for item in playback if isinstance(item, dict)]
    return None


def _unit_error(report_type: str, units: list[dict[str, Any]] | None) -> dict[str, Any] | None:
    if units is None:
        return result(report_type, errors=["playback map must contain canonical units or segments; token-only input is incomplete"])
    return None


def _candidate(kind: str, left: dict[str, Any], right: dict[str, Any], reason: str) -> dict[str, Any]:
    return {"scan": kind, "action": "review", "start_us": left.get("start_us", left.get("edited_start_us")), "end_us": right.get("end_us", right.get("edited_end_us")), "unit_ids": [left.get("id"), right.get("id")], "reason": reason, "flags": ["human_review"]}


def detect_repetition_candidates(playback: Any) -> dict[str, Any]:
    units = _units(playback)
    if (error := _unit_error("repetition_candidates", units)) is not None:
        return error
    candidates = []
    for left, right in pairwise(units):
        a, b = str(left.get("text", "")).strip(), str(right.get("text", "")).strip()
        if a and b and difflib.SequenceMatcher(None, a, b).ratio() >= 0.86:
            candidates.append(_candidate("repetition", left, right, "adjacent units are text-similar; check whether either adds meaning"))
    return result("repetition_candidates", data={"candidates": candidates}, summary={"candidate_count": len(candidates)})


def detect_false_start_candidates(playback: Any) -> dict[str, Any]:
    units = _units(playback)
    if (error := _unit_error("false_start_candidates", units)) is not None:
        return error
    candidates = []
    for left, right in pairwise(units):
        text = str(left.get("text", ""))
        if text and len(text) <= 8 and not re.search(r"[。！？.!?]$", text) and right.get("text"):
            candidates.append(_candidate("false_start", left, right, "short non-terminal fragment before a following unit"))
    return result("false_start_candidates", data={"candidates": candidates}, summary={"candidate_count": len(candidates)})


def detect_misspoken_retake_candidates(playback: Any) -> dict[str, Any]:
    units = _units(playback)
    if (error := _unit_error("misspoken_retake_candidates", units)) is not None:
        return error
    markers = ("不对", "应该", "不是", "准确说", "更正")
    candidates = []
    for left, right in pairwise(units):
        if any(marker in str(right.get("text", "")) for marker in markers):
            candidates.append(_candidate("misspoken_retake", left, right, "later unit contains a self-correction marker; verify the complete accurate take"))
    return result("misspoken_retake_candidates", data={"candidates": candidates}, summary={"candidate_count": len(candidates)})


def detect_english_stutter_candidates(playback: Any) -> dict[str, Any]:
    units = _units(playback)
    if (error := _unit_error("english_stutter_candidates", units)) is not None:
        return error
    candidates = []
    pattern = re.compile(r"\b([A-Za-z])(?:[- ]\1){1,}\b", re.IGNORECASE)
    for unit in units:
        if pattern.search(str(unit.get("text", ""))):
            candidates.append({"scan": "english_stutter", "action": "review", "start_us": unit.get("start_us", unit.get("edited_start_us")), "end_us": unit.get("end_us", unit.get("edited_end_us")), "unit_ids": [unit.get("id")], "reason": "repeated English initial detected", "flags": ["human_review"]})
    return result("english_stutter_candidates", data={"candidates": candidates}, summary={"candidate_count": len(candidates)})


def detect_filler_candidates(playback: Any, preferences: Any = None) -> dict[str, Any]:
    units = _units(playback)
    if (error := _unit_error("filler_candidates", units)) is not None:
        return error
    configured = preferences.get("fillers") if isinstance(preferences, dict) else None
    fillers = set(configured or ("那个", "然后然后", "嗯嗯", "呃呃", "啊啊"))
    candidates = []
    for unit in units:
        text = str(unit.get("text", ""))
        if text in fillers or len(re.findall(r"(?:那个|嗯|呃|啊)", text)) >= 2:
            candidates.append({"scan": "filler", "action": "review", "start_us": unit.get("start_us", unit.get("edited_start_us")), "end_us": unit.get("end_us", unit.get("edited_end_us")), "unit_ids": [unit.get("id")], "reason": "possible filler run; preserve meaningful discourse markers", "flags": ["human_review"]})
    return result("filler_candidates", data={"candidates": candidates}, summary={"candidate_count": len(candidates)})


def _audio_pauses_from_file(path: str, config: dict[str, Any]) -> tuple[list[dict[str, int]], str | None]:
    if not Path(path).exists():
        return [], f"audio path does not exist: {path}"
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return [], "ffmpeg unavailable; provide precomputed pause intervals"
    noise = str(config.get("noise_db", "-35dB"))
    minimum_s = float(config.get("pause_min_us", 120000)) / 1_000_000
    completed = subprocess.run(
        [ffmpeg, "-hide_banner", "-i", path, "-af", f"silencedetect=noise={noise}:d={minimum_s}", "-f", "null", "-"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if completed.returncode != 0:
        return [], completed.stderr.strip() or "ffmpeg silencedetect failed"
    starts: list[int] = []
    pauses: list[dict[str, int]] = []
    for line in completed.stderr.splitlines():
        start_match = re.search(r"silence_start:\s*([0-9.]+)", line)
        end_match = re.search(r"silence_end:\s*([0-9.]+)", line)
        if start_match:
            starts.append(round(float(start_match.group(1)) * 1_000_000))
        if end_match and starts:
            start = starts.pop(0)
            end = round(float(end_match.group(1)) * 1_000_000)
            if end >= start:
                pauses.append({"start_us": start, "end_us": end})
    return pauses, None


def detect_pause_candidates(audio: Any, config: Any = None) -> dict[str, Any]:
    config = config if isinstance(config, dict) else {}
    # Only detector settings may be echoed. Unknown metadata could carry action
    # instructions and must not become part of a candidate report.
    detector_fields = {"pause_min_us", "noise_db"}
    shared_waveform_fields = {
        "pause_cap_us", "edge_window_us", "tolerance_us", "hop_us", "window_us",
        "auto_snap_within_tolerance",
    }
    if set(config) - detector_fields - shared_waveform_fields:
        return result("pause_candidates", errors=["pause config accepts detector settings only"])
    # Workflow bundles share config with waveform alignment. These settings
    # have no authority here and are not echoed as candidate instructions.
    config = {key: value for key, value in config.items() if key in detector_fields}
    minimum = config.get("pause_min_us", 120000)
    if not isinstance(minimum, int) or isinstance(minimum, bool) or minimum < 0:
        return result("pause_candidates", errors=["pause_min_us must be a non-negative integer"])
    noise = config.get("noise_db", "-35dB")
    if not isinstance(noise, str) or not re.fullmatch(r"-?\d+(?:\.\d+)?dB", noise):
        return result("pause_candidates", errors=["noise_db must be a numeric dB string"])
    pauses = []
    source_error = None
    # A workflow may already have paid for the waveform pass.  Consume its
    # normalized pauses before looking at the path so scan-all does not invoke
    # ffmpeg a second time for the same audio.
    if isinstance(audio, dict) and isinstance(audio.get("pauses"), list):
        pauses = audio.get("pauses", [])
    elif isinstance(audio, str):
        if not Path(audio).exists():
            return result("pause_candidates", input_errors=[f"audio path does not exist: {audio}"])
        pauses, source_error = _audio_pauses_from_file(audio, config)
    elif isinstance(audio, dict) and isinstance(audio.get("path"), str):
        if not Path(audio["path"]).exists():
            return result("pause_candidates", input_errors=[f"audio path does not exist: {audio['path']}"])
        pauses, source_error = _audio_pauses_from_file(audio["path"], config)
    elif audio is None:
        return result("pause_candidates", errors=["audio evidence is required for pause scanning"])
    else:
        return result("pause_candidates", errors=["audio input must be a media path or precomputed pause list"])
    candidates = []
    for pause in pauses if isinstance(pauses, list) else []:
        if not isinstance(pause, dict):
            source_error = source_error or "precomputed pause evidence contains a non-object"
            continue
        start, end = pause.get("start_us"), pause.get("end_us")
        if not isinstance(start, int) or isinstance(start, bool) or not isinstance(end, int) or isinstance(end, bool) or start < 0 or end <= start:
            source_error = source_error or "precomputed pause evidence contains invalid boundaries"
            continue
        if end - start >= minimum:
            candidates.append({
                "scan": "pause", "action": "review", "candidate_only": True,
                "start_us": start, "end_us": end, "duration_us": end - start,
                "pause_function": "unavailable", "contextual_review_required": True,
                "provenance": "script_generated", "human_review": True,
                "human_listening": "pending",
                "reason": "waveform pause meets configured candidate threshold; function needs context",
                "flags": ["needs_listen", "human_review"],
            })
    return result("pause_candidates", data={"candidates": candidates, "config": config,
                  "pause_function_options": list(PAUSE_FUNCTIONS)},
                  errors=[source_error] if source_error else [], summary={"candidate_count": len(candidates)})


def scan_all(playback: Any, preferences: Any = None, audio: Any = None, pause_config: Any = None) -> dict[str, Any]:
    reports = [
        detect_repetition_candidates(playback),
        detect_false_start_candidates(playback),
        detect_misspoken_retake_candidates(playback),
        detect_english_stutter_candidates(playback),
        detect_filler_candidates(playback, preferences),
    ]
    warnings = ["all candidates require contextual listening"]
    pause_scan_status = "not_executed"
    if audio is not None:
        reports.append(detect_pause_candidates(audio, pause_config))
        pause_scan_status = "executed"
    else:
        warnings.append("pause scan skipped: audio evidence was not provided")
    candidates = [
        item
        for report in reports
        for item in ((report.get("data") or {}).get("candidates", []) if isinstance(report.get("data"), dict) else [])
    ]
    errors = [error for report in reports for error in report.get("errors", [])]
    input_errors = [error for report in reports for error in report.get("input_errors", [])]
    return result("candidate_scans", data={"scans": reports, "candidates": candidates, "pause_scan_status": pause_scan_status}, errors=errors, input_errors=input_errors, warnings=warnings, summary={"candidate_count": len(candidates), "scan_count": len(reports)})
