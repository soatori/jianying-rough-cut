"""Import timed word-level transcript output from supported ASR tools."""

from __future__ import annotations

import math
from typing import Any

from .result import result


def _seconds_to_us(value: Any, path: str, errors: list[str]) -> int | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        errors.append(f"{path}: must be a finite number of seconds")
        return None
    if not math.isfinite(float(value)):
        errors.append(f"{path}: must be a finite number of seconds")
        return None
    return round(float(value) * 1_000_000)


def import_ai_jian_koubo_whisperx(payload: Any) -> dict[str, Any]:
    """Convert AI剪口播 ``whisperx_result.json`` to the canonical transcript shape.

    The source JSON uses seconds for utterance bounds and integer milliseconds
    for word bounds. The importer preserves ASR wording and timing; it does not
    correct text or treat an ASR utterance as a final semantic unit.
    """

    if not isinstance(payload, dict):
        return result("transcript_import", input_errors=["WhisperX result must be a JSON object"])

    validation = payload.get("validation")
    if not isinstance(validation, dict) or validation.get("timing_valid") is not True:
        return result(
            "transcript_import",
            errors=["validation.timing_valid must be true before transcript import"],
        )

    source_result = payload.get("result")
    utterances = source_result.get("utterances") if isinstance(source_result, dict) else None
    if not isinstance(utterances, list) or not utterances:
        return result(
            "transcript_import",
            errors=["result.utterances must be a non-empty array"],
        )

    errors: list[str] = []
    segments: list[dict[str, Any]] = []
    token_count = 0
    previous_start_us = -1

    for segment_index, utterance in enumerate(utterances, start=1):
        path = f"result.utterances[{segment_index - 1}]"
        if not isinstance(utterance, dict):
            errors.append(f"{path}: must be an object")
            continue

        text = utterance.get("text")
        if not isinstance(text, str) or not text.strip():
            errors.append(f"{path}.text: must be a non-empty string")

        start_us = _seconds_to_us(utterance.get("start"), f"{path}.start", errors)
        end_us = _seconds_to_us(utterance.get("end"), f"{path}.end", errors)
        if start_us is not None and end_us is not None:
            if start_us < 0 or end_us <= start_us:
                errors.append(f"{path}: start/end must be a positive, increasing range")
            if start_us < previous_start_us:
                errors.append(f"{path}.start: utterances must be ordered by start time")
            previous_start_us = start_us

        raw_words = utterance.get("words")
        if not isinstance(raw_words, list) or not raw_words:
            errors.append(f"{path}.words: non-empty word-level timestamps are required")
            continue

        segment_id = f"segment-{segment_index:06d}"
        tokens: list[dict[str, Any]] = []
        previous_token_start_us = -1
        for word_index, word in enumerate(raw_words, start=1):
            word_path = f"{path}.words[{word_index - 1}]"
            if not isinstance(word, dict):
                errors.append(f"{word_path}: must be an object")
                continue
            word_text = word.get("text")
            word_start_ms = word.get("start_time")
            word_end_ms = word.get("end_time")
            if not isinstance(word_text, str) or not word_text:
                errors.append(f"{word_path}.text: must be a non-empty string")
            if (
                isinstance(word_start_ms, bool)
                or not isinstance(word_start_ms, int)
                or isinstance(word_end_ms, bool)
                or not isinstance(word_end_ms, int)
            ):
                errors.append(f"{word_path}: start_time/end_time must be integer milliseconds")
                continue

            token_start_us = word_start_ms * 1_000
            token_end_us = word_end_ms * 1_000
            if token_start_us < 0 or token_end_us <= token_start_us:
                errors.append(f"{word_path}: start_time/end_time must be a positive, increasing range")
            if token_start_us < previous_token_start_us:
                errors.append(f"{word_path}.start_time: words must be ordered by start time")
            previous_token_start_us = token_start_us
            if start_us is not None and end_us is not None and (
                token_start_us < start_us - 1_000 or token_end_us > end_us + 1_000
            ):
                errors.append(f"{word_path}: word range falls outside its utterance")

            tokens.append({
                "id": f"token-{segment_index:06d}-{word_index:06d}",
                "semantic_unit_id": segment_id,
                "text": word_text,
                "start_us": token_start_us,
                "end_us": token_end_us,
            })

        token_count += len(tokens)
        if start_us is not None and end_us is not None:
            segments.append({
                "id": segment_id,
                "semantic_unit_id": segment_id,
                "text": text.strip() if isinstance(text, str) else "",
                "start_us": start_us,
                "end_us": end_us,
                "tokens": tokens,
            })

    if errors:
        return result("transcript_import", errors=errors)

    upstream_warnings = validation.get("warnings", [])
    warnings = [
        "ASR utterance boundaries are timing containers, not approved semantic units; review and regroup before content decisions."
    ]
    if isinstance(upstream_warnings, list):
        warnings.extend(str(item) for item in upstream_warnings if isinstance(item, str) and item.strip())

    transcript = {
        "segments": segments,
        "source": {
            "format": "ai-jian-koubo-whisperx",
            "segmentation_role": "timing_container",
            "semantic_boundaries_status": "unverified",
        },
        "unresolved_terms": [],
    }
    return result(
        "transcript_import",
        data=transcript,
        warnings=warnings,
        summary={"segment_count": len(segments), "token_count": token_count},
    )
