# Subtitle proofreading and audio alignment

This stage runs after the rough-cut content pass has been executed and before packaging begins. It corrects the current Jianying-recognized subtitles against the edited timeline; it is not a packaging operation.

## Inputs and order

1. Save and probe the current edited timeline through `jianying-editor`.
2. Reconstruct the edited timeline audio from the current segment order, source ranges, speed, and handles where applicable.
3. Read the current recognized text and compare it with the actual speech.
4. Correct names, terms, numbers, units, models, negation, conditions, causality, and ASR segmentation.
5. Use listening and waveform evidence to propose boundaries.
6. Review the complete subtitle list in context, then output an application-independent `subtitle_alignment_plan`.
7. After human approval, let `jianying-editor` resolve the semantic ranges to current draft segments and apply the plan.
8. Independently read back and validate before marking `subtitle_alignment=approved`.

If a later rough-cut change changes source order, source range, speed, or duration, repeat this stage. A packaging-only style change does not require full re-alignment unless it changes subtitle timing or segmentation.

## Anchor units, not seconds

A subtitle screen stores a list of stable word/semantic-unit references plus the display text — **not** absolute seconds. Post-cut time is *computed* each pass from (token time in the source) + (which ranges the edit list kept):

- token's source time → already in the time-coded transcript;
- which segments survive → in the content decision plan / edit list;
- token's edited-timeline time → arithmetic of the two, with no approximation.

Do not re-run ASR on the edited video to recover timing: it re-listens to the same speech, costs time, and forces every proper noun to be re-corrected. Do not stitch the **original** subtitle cues head-to-tail along the edit list either — those cue boundaries were cut on the original's pauses, so pasted after an edit they drift further and further off. Only the per-token mapping survives editing intact.

Subtitles may legitimately differ in text from the transcript (punctuation, removed fillers, official spellings); that divergence is intentional. The transcript answers "what was said"; the subtitle answers "what the viewer reads".

## Segmentation ladder

Break screens by the highest-priority rule that applies, in this order:

1. **A deletion happened here** — but only a removal of *speech*; two sides of a removed *silence* are still one sentence, so do not split a sentence just because a pause was trimmed.
2. **Any punctuation** — same granularity as the cleanup script's sentence segmentation, so the cut pass and the subtitle pass break at the same place. Punctuation outranks any timing signal: a speaker may run two sentences without breathing, or pause mid-sentence.
3. **Paragraph edge + pause** — used only when a token carries no punctuation.
4. **A genuinely long audible pause** — to split an over-long sentence internally.

Fragment handling: merge a one-to-two-character fragment back as the tail of the previous screen, but **never across a sentence period** (a short opener like "你看" starts a new sentence; merging it forward glues two sentences together). If splitting produces such a fragment, that boundary was not a real period — merge it back. A short screen from fast speech is not a defect and must not be flagged: warning on normal speech only teaches reviewers to ignore warnings. Flag only `tooFast` (a screen with more text than its dwell time can be read).

## Hybrid boundary policy

Use audio as the default boundary authority. Use local picture-lock only when the picture provides a real semantic constraint:

- do not split a continuous word or phrase only because a shot cuts;
- snap to a shot boundary when it coincides with a natural pause, sentence boundary, speaker change, or deliberate visual binding;
- use local picture-lock for parameters, devices, values, or steps that must remain attached to the visible object;
- send audio/picture conflicts to human review.

Record `mode`, `basis`, evidence, confidence, and review status for both the start and end of every subtitle unit.

## Evidence cautions

Waveform and silence thresholds locate candidates; they do not authorize deletion or splitting by themselves. The current project may use values such as a 10ms hop, 25ms window, 120ms pause floor, and 350ms cap, but those are configurable detector defaults.

Word-level timestamps are a cross-check. If their health check fails or the text and timing disagree, fall back to audio, semantics, and manual listening rather than treating word times as authoritative.

## Deprecated practices

Recognize and reject these obsolete patterns; do not reintroduce them.

- **Overwriting existing subtitles without asking.** A rebuild replaces the screens, wording, and breaks a human already tuned — and nothing downstream can recover them. Editing a few characters is not a rebuild: change those units in place. A full overwrite is the one operation in this stage that requires explicit confirmation first.
- **Re-running ASR on the edited video to recover timing.** Obsolete. Post-cut time is computed from token source-times plus the kept ranges ([Anchor units, not seconds](#anchor-units-not-seconds)); a second transcription only re-hears the same speech and forces every proper noun to be re-corrected.
- **Stitching the original subtitle cues head-to-tail along the edit list.** Those cue boundaries were cut on the original's pauses and drift after an edit. Only the per-token/semantic-unit mapping survives.
- **Keeping ASR cue boundaries as subtitle screens.** Segment by the punctuation ladder above, not by whatever breaks the recognizer happened to emit.
- **Treating the subtitle stage as a fixed pipeline step.** It is a standalone operation: run it whenever the account ledger (decision plan / edit list) and time-coded transcript exist, and re-run it after any change that moves, deletes, or re-times surviving speech.
