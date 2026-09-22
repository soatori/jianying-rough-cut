"""Generate application-independent subtitle units and SRT previews.

This module accepts timed transcript evidence only.  It does not run ASR and
it does not know anything about Jianying's project format.  The generated
units are later passed through the same waveform-first alignment builder used
for subtitles that already exist on a saved timeline.
"""

from __future__ import annotations

import copy
from typing import Any

from .result import result


def _timed_integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _segment_text(segment: dict[str, Any]) -> str:
    text = segment.get("text")
    if isinstance(text, str) and text.strip():
        return text.strip()
    words = segment.get("words", segment.get("tokens"))
    if not isinstance(words, list):
        return ""
    return "".join(
        item.get("text", "")
        for item in words
        if isinstance(item, dict) and isinstance(item.get("text"), str)
    ).strip()


def _timed_word_bounds(segment: dict[str, Any]) -> tuple[int, int] | None:
    words = segment.get("words", segment.get("tokens"))
    if not isinstance(words, list) or not words:
        return None
    bounds: list[tuple[int, int]] = []
    for word in words:
        if not isinstance(word, dict):
            return None
        start_us = word.get("start_us")
        end_us = word.get("end_us")
        if (
            not _timed_integer(start_us)
            or not _timed_integer(end_us)
            or start_us < 0
            or end_us <= start_us
        ):
            return None
        bounds.append((start_us, end_us))
    return min(start for start, _ in bounds), max(end for _, end in bounds)


def _corrections_by_segment(corrections: Any) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    if not isinstance(corrections, list):
        return grouped
    for item in corrections:
        if not isinstance(item, dict) or item.get("segment_id") is None:
            continue
        segment_id = str(item["segment_id"])
        grouped.setdefault(segment_id, []).append(copy.deepcopy(item))
    return grouped


def build_generated_subtitle_units(transcript: Any, corrections: Any = None) -> dict[str, Any]:
    """Convert timed transcript segments into pending subtitle units.

    Segment and word timestamps are evidence, not final subtitle boundaries.
    The caller must pass the returned units through waveform alignment before
    treating them as a subtitle plan.
    """

    if not isinstance(transcript, dict):
        return result("subtitle_generation", input_errors=["timed transcript must be a JSON object"])

    segments = transcript.get("segments")
    if segments is None:
        segments = transcript.get("units")
    if not isinstance(segments, list) or not segments:
        return result(
            "subtitle_generation",
            input_errors=["timed transcript must contain a non-empty segments or units array"],
        )

    errors: list[str] = []
    warnings: list[str] = []
    units: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    seen_semantic_ids: set[str] = set()
    corrections_by_segment = _corrections_by_segment(corrections)

    for index, raw in enumerate(segments):
        path = f"transcript.segments[{index}]"
        if not isinstance(raw, dict):
            errors.append(f"{path} must be an object")
            continue

        subtitle_id = str(raw.get("id", f"subtitle-{index + 1}"))
        semantic_id = str(raw.get("semantic_unit_id", raw.get("id", subtitle_id)))
        if subtitle_id in seen_ids:
            errors.append(f"{path} duplicates id {subtitle_id!r}")
        if semantic_id in seen_semantic_ids:
            errors.append(f"{path} duplicates semantic_unit_id {semantic_id!r}")
        seen_ids.add(subtitle_id)
        seen_semantic_ids.add(semantic_id)

        text = _segment_text(raw)
        if not text:
            errors.append(f"{path}.text or timed words are required")

        start_us = raw.get("start_us")
        end_us = raw.get("end_us")
        word_bounds = _timed_word_bounds(raw)
        if not _timed_integer(start_us) or start_us < 0:
            if word_bounds is not None:
                start_us = word_bounds[0]
            else:
                errors.append(f"{path}.start_us must be a non-negative integer or derivable from timed words")
                start_us = 0
        if not _timed_integer(end_us) or end_us <= start_us:
            if word_bounds is not None and word_bounds[1] > start_us:
                end_us = word_bounds[1]
            else:
                errors.append(f"{path}.end_us must be after start_us or derivable from timed words")
                end_us = start_us + 1

        unit: dict[str, Any] = {
            "id": subtitle_id,
            "semantic_unit_id": semantic_id,
            "text": text,
            "start_us": start_us,
            "end_us": end_us,
            "review_status": "pending",
            "corrections": corrections_by_segment.get(str(raw.get("id", subtitle_id)), []),
        }
        words = raw.get("words", raw.get("tokens"))
        if words is not None:
            if not isinstance(words, list):
                errors.append(f"{path}.words/tokens must be an array when present")
            else:
                unit["words"] = copy.deepcopy(words)
        units.append(unit)

    unresolved_terms = transcript.get("unresolved_terms", [])
    if unresolved_terms is None:
        unresolved_terms = []
    if not isinstance(unresolved_terms, list):
        errors.append("transcript.unresolved_terms must be an array when present")
        unresolved_terms = []
    if unresolved_terms:
        warnings.append("unresolved transcript terms remain; human proofreading is required")

    data = {
        "subtitle_units": units,
        "unresolved_terms": copy.deepcopy(unresolved_terms),
        "corrections": copy.deepcopy(corrections) if isinstance(corrections, list) else [],
        "source": {
            "segmentation_source": "timed_transcript_segments",
            "text_source": "corrected_timed_transcript",
        },
    }
    return result(
        "subtitle_generation",
        data=data,
        errors=errors,
        warnings=warnings,
        summary={
            "subtitle_unit_count": len(units),
            "correction_count": len(data["corrections"]),
            "unresolved_term_count": len(unresolved_terms),
        },
    )


def _srt_timestamp(microseconds: int) -> str:
    milliseconds = microseconds // 1_000
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, millis = divmod(remainder, 1_000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def render_srt(plan_or_units: Any) -> str:
    """Render selected subtitle ranges as UTF-8 SRT text.

    Start times are rounded down and end times rounded up to milliseconds so
    conversion never shortens a pending waveform range.  The SRT is a review
    artifact and carries no Jianying identifiers or write instructions.
    """

    duration_us: int | None = None
    if isinstance(plan_or_units, dict) and isinstance(plan_or_units.get("subtitle_units"), list):
        units = plan_or_units["subtitle_units"]
        source = plan_or_units.get("source")
        if isinstance(source, dict) and _timed_integer(source.get("duration_us")) and source["duration_us"] > 0:
            duration_us = source["duration_us"]
    else:
        units = plan_or_units
    if not isinstance(units, list) or not units:
        raise ValueError("subtitle units are required to render SRT")

    blocks: list[str] = []
    previous_start = -1
    previous_end = -1
    for index, unit in enumerate(units, start=1):
        if not isinstance(unit, dict):
            raise TypeError(f"subtitle_units[{index - 1}] must be an object")
        text = unit.get("text")
        start_us = unit.get("start_us")
        end_us = unit.get("end_us")
        if not isinstance(text, str) or not text.strip():
            raise ValueError(f"subtitle_units[{index - 1}].text must be non-empty")
        if not _timed_integer(start_us) or not _timed_integer(end_us) or start_us < 0 or end_us <= start_us:
            raise ValueError(f"subtitle_units[{index - 1}] has invalid microsecond range")
        if duration_us is not None and end_us > duration_us:
            raise ValueError(f"subtitle_units[{index - 1}].end_us exceeds audio duration")
        if start_us < previous_start:
            raise ValueError("subtitle units must be ordered by start_us")
        if end_us < previous_end:
            raise ValueError("subtitle units must have non-decreasing end_us")
        previous_start = start_us
        previous_end = end_us
        start_ms = start_us // 1_000
        end_ms = (end_us + 999) // 1_000
        if end_ms <= start_ms:
            end_ms = start_ms + 1
        normalized_text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
        blocks.append(
            "\n".join(
                (
                    str(index),
                    f"{_srt_timestamp(start_ms * 1_000)} --> {_srt_timestamp(end_ms * 1_000)}",
                    normalized_text,
                )
            )
        )
    return "\n\n".join(blocks) + "\n"


__all__ = ["build_generated_subtitle_units", "render_srt"]
