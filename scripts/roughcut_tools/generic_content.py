"""Generic-content guard for reusable rough-cut Skill files."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

from .result import result


TEXT_SUFFIXES = {".md", ".json", ".py", ".yaml", ".yml", ".txt", ".csv"}
PATTERNS = {
    "absolute_path": re.compile(r"(?i)(?<![A-Za-z0-9_])[A-Z]:[\\/][^\\s\"']+"),
    "draft_path": re.compile(r"(?i)jianyingpro[\\/].*(?:drafts|timelines|draft_content\.json)"),
    "guid": re.compile(r"(?i)(?<![0-9a-f])[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}(?![0-9a-f])"),
    "media_filename": re.compile(r"(?i)(?:^|[\\/\s\"'])[^<>\\/\s\"']+\.(?:mp4|mov|mkv|avi|wav|mp3|m4a|png|jpg|jpeg|webp)\b"),
}


def scan(roots: list[str | Path], forbidden_literals: Iterable[str] | None = None) -> list[str]:
    forbidden = [item for item in (forbidden_literals or []) if isinstance(item, str) and item]
    findings: list[str] = []
    for root_value in roots:
        root = Path(root_value)
        files = [root] if root.is_file() else [path for path in root.rglob("*") if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES]
        for path in files:
            if "__pycache__" in path.parts:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            for name, pattern in PATTERNS.items():
                if pattern.search(text):
                    findings.append(f"{path}: {name}")
            for literal in forbidden:
                if literal in text:
                    findings.append(f"{path}: forbidden_literal:{literal}")
    return findings


def check_generic_content(roots: list[str | Path], forbidden_literals: Iterable[str] | None = None) -> dict:
    findings = scan(roots, forbidden_literals)
    return result(
        "roughcut_generic_content_validation",
        data={"findings": findings},
        errors=findings,
        summary={"finding_count": len(findings)},
    )
