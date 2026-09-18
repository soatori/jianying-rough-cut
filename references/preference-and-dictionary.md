# Preference and dictionary learning loop (Pass 3)

This skill improves only by remembering what a human corrected. After the human reviews an executed result, run this retrospective and persist the lessons. This stage writes learning files only; it never mutates a Jianying draft or a plan that has already shipped.

## Two dictionaries, one preference file

- **General dictionary** — the shipped baseline of common ASR misrecognitions (proper nouns, product names, acronyms). See [asr-term-dictionary.md](asr-term-dictionary.md) for format and the seeded entries. Applies to every project.
- **Per-user dictionary** — one persistent file the user owns, holding *their* recurring proper nouns and preferred spellings. It overrides the general dictionary. Create it on first use; append after de-duplication.
- **Preference file** — the user's taste: how aggressively to cut fillers, pause tolerance, which discourse markers to keep, platform pace. It governs the refinement scan thresholds.

Precedence when they conflict: **user preference > user case-law > general case-law > general dictionary defaults.**

## Dictionary entry format

A dictionary is a plain table; only table rows are parsed, so prose or bullet lists are silently ignored. Two columns:

```markdown
| 正确写法 | 常见误识别 |
| --- | --- |
| Grok | grok / Clock / Glock / Gokul / 格罗克 |
```

- Pick the most frequent confirmed spelling as canonical; on ties use the official spelling.
- Never map a term to a translation or a "better" word. Same-name spelling variants and clear mishearings only.
- If a term appears but no spelling of it can be confirmed, do not invent one — report it and add it here once a human settles it.

## The retrospective diff

Compare the approved proposal (kept in the task folder) against the final human-reviewed plan:

- **Restored by the human** (in the proposal, gone from the final) = the cut was wrong. Ask against the recorded `reason`: which category did it fall into, and why?
- **Added by the human** (in the final, not in the proposal) = the cut was missed. Ask which type it is and why it was not detected.

A zero-diff result is still recorded: append one line "fully adopted" to the preference file. Do not silently discard the human's edits — the diff is the only learning signal.

## Three drawers

- **Taste differences** → append to the preference file. Own the phrasing; only add or rewrite your own sections.
- **Proper-noun corrections** → append to the per-user dictionary (de-duplicate before adding).
- **Rule gaps** → record one line in the preference file's `待升级判例` / "pending-cases" section. On the **third** occurrence of the same kind, report it and propose promoting the pattern into the shared case-law in [cut-case-law.md](cut-case-law.md). Promotion into the skill files happens only after human approval, never automatically.

## Confidence feedback

A decision type the human keeps restoring should raise the review bar (and may be reclassified from destructive to `review`) in future runs; a pattern the human keeps adding should be pulled earlier into the scan list. Note the adjustment in the preference file next to the case so the next orientation stage reads it.
