"""Dictionary-only transcript correction gate."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .result import result


def load_dictionary(path: str | Path) -> dict[str, str]:
    text = Path(path).read_text(encoding="utf-8-sig")
    if Path(path).suffix.lower() == ".json":
        data = json.loads(text)
        if isinstance(data, dict):
            if all(isinstance(key, str) and isinstance(value, str) for key, value in data.items()):
                return data
            raise ValueError("dictionary JSON values must be strings")
        raise ValueError("dictionary JSON must be an object mapping variants to canonical terms")
    mapping: dict[str, str] = {}
    for line in text.splitlines():
        if not line.strip().startswith("|") or "---" in line:
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 2 or cells[0] in {"正确写法", "canonical"}:
            continue
        canonical = cells[0]
        for variant in re.split(r"\s*/\s*|\s*,\s*", cells[1]):
            if variant.strip():
                mapping[variant.strip()] = canonical
    return mapping


def _replace_text(text: str, mapping: dict[str, str]) -> tuple[str, list[dict[str, str]]]:
    corrections: list[dict[str, str]] = []
    updated = text
    for variant, canonical in sorted(mapping.items(), key=lambda item: len(item[0]), reverse=True):
        if variant == canonical or variant not in updated:
            continue
        updated = updated.replace(variant, canonical)
        corrections.append({"original": variant, "corrected": canonical, "context": text})
    return updated, corrections


def apply_dictionary_corrections(transcript: Any, dictionaries: list[dict[str, str]]) -> dict[str, Any]:
    if not isinstance(transcript, dict):
        return result("transcript_correction", errors=["transcript must be a JSON object"])
    if not isinstance(dictionaries, list):
        return result("transcript_correction", input_errors=["dictionaries must be an array"])
    mapping: dict[str, str] = {}
    dictionary_errors: list[str] = []
    for index, dictionary in enumerate(dictionaries):
        if not isinstance(dictionary, dict):
            dictionary_errors.append(f"dictionary[{index}] must be an object")
            continue
        for variant, canonical in dictionary.items():
            if not isinstance(variant, str) or not variant or not isinstance(canonical, str) or not canonical:
                dictionary_errors.append(f"dictionary[{index}] entries must map non-empty strings")
                continue
            mapping[variant] = canonical
    if dictionary_errors:
        return result("transcript_correction", errors=dictionary_errors)
    corrected = json.loads(json.dumps(transcript, ensure_ascii=False))
    corrections: list[dict[str, Any]] = []
    segments = corrected.get("segments", corrected.get("units", []))
    for segment in segments if isinstance(segments, list) else []:
        if not isinstance(segment, dict):
            continue
        if isinstance(segment.get("text"), str):
            old = segment["text"]
            new, rows = _replace_text(old, mapping)
            if new != old:
                segment["text"] = new
                corrections.extend({"segment_id": segment.get("id"), **row} for row in rows)
        for token_key in ("tokens", "words"):
            token_list = segment.get(token_key)
            if not isinstance(token_list, list):
                continue
            for token in token_list:
                if not isinstance(token, dict) or not isinstance(token.get("text"), str):
                    continue
                old, new = token["text"], token["text"]
                new, rows = _replace_text(new, mapping)
                if new != old:
                    token["text"] = new
                    corrections.extend(
                        {"segment_id": segment.get("id"), "token_id": token.get("id"), **row}
                        for row in rows
                    )
    unresolved = list(transcript.get("unresolved_terms", []))
    return result("transcript_correction", data={"transcript": corrected, "corrections": corrections, "unresolved_terms": unresolved}, summary={"correction_count": len(corrections), "unresolved_count": len(unresolved)})
