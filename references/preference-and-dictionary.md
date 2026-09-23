# Preference and dictionary learning loop (Pass 3)

This skill improves only by remembering what a human corrected. After the human reviews an executed result, run this retrospective and produce a learning report. The tool layer does not write user dictionaries, preference files, case-law, drafts, or shipped plans; a human-approved workflow may persist the reported entries afterward.

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

A zero-diff result is still recorded as a `fully_adopted` report entry. Do not silently discard the human's edits — the diff is the only learning signal.

Always persist the approved decision/packaging plan JSON into the draft's working folder while executing, so this Pass 3 diff has a reproducible source. When no plan was persisted, fall back to the draft's own autosave history: decode the `.backup/*.save.bak` snapshots plus the root active-mirror timeline and reconstruct a coarse before→after (track/segment/text/color/animation counts). This reconstruction is file-level (`plan_consistency`) evidence only — it cannot prove perceptual or listening outcomes, so downgrade any conclusion it supports to `review`.

## Where persistence lives

- **Reusable skill files hold generic methods only.** Never write a single project's concrete palette, wording, per-word colors, exact coordinates, or client terms into the shipped skill; that is content, not procedure. A generic layout scheme (how emphasis rows surround/stack relative to the subtitle baseline) is method and may live in the skill; the actual values a project settles on are not.
- **Durable per-project taste and lexicon go to the user-owned external stores** — the per-user dictionary, the preference file, and the project case reference — which the skills load at runtime. They are the only correct home for confirmed proper nouns, thresholds, and a project's measured layout/color/animation values.
- **Do not force project knowledge into the volatile agent long-term memory**, which is size-capped and will silently reject or thrash writes near capacity. When a durable lesson is project-specific, write it to the case reference / preference file, not to agent memory.

## Three drawers

- **Taste differences** → report a pending preference suggestion. Own the phrasing; only add or rewrite your own sections after approval.
- **Proper-noun corrections** → report only an explicitly human-confirmed correction for the per-user dictionary; never infer a canonical spelling from a diff.
- **Rule gaps** → report a pending case. On the **third** occurrence of the same kind, report it and propose promoting the pattern into the shared case-law in [cut-case-law.md](cut-case-law.md). Promotion into the skill files happens only after human approval, never automatically.

## Confidence feedback

A decision type the human keeps restoring should raise the review bar (and may be reclassified from destructive to `review`) in future runs; a pattern the human keeps adding should be pulled earlier into the scan list. Note the adjustment in the preference file next to the case so the next orientation stage reads it.
