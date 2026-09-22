"""Build bounded review windows around rough-cut candidates."""

from __future__ import annotations

from typing import Any

from .result import result


def build_review_snippets(candidates: Any, media: Any) -> dict[str, Any]:
    rows = candidates.get("candidates", []) if isinstance(candidates, dict) else candidates
    duration = media.get("duration_us") if isinstance(media, dict) else None
    padding = int(media.get("padding_us", 120000)) if isinstance(media, dict) else 120000
    snippets = []
    for index, candidate in enumerate(rows if isinstance(rows, list) else []):
        if not isinstance(candidate, dict):
            continue
        start = candidate.get("start_us")
        end = candidate.get("end_us")
        if not isinstance(start, int) or not isinstance(end, int):
            continue
        left = max(0, start - padding)
        right = end + padding
        if isinstance(duration, int):
            right = min(duration, right)
        snippets.append({"id": f"review-{index + 1:04d}", "candidate_index": index, "start_us": left, "end_us": right, "reason": candidate.get("reason"), "source": candidate})
    return result("review_snippets", data={"snippets": snippets}, summary={"snippet_count": len(snippets)})
