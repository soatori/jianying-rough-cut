# Subtitle proofreading and audio alignment

This stage runs after the rough-cut content pass has been executed and before packaging begins. It is not a packaging operation and it has two explicit input modes:

- `existing`: the current visible subtitle list is authoritative for wording,
  order, and segmentation; waveform evidence supplies boundary candidates.
- `generate`: the timeline has no subtitles and an external/local transcript
  supplies timed segments or words; dictionary correction changes wording only,
  then waveform evidence supplies boundary candidates.

The rough-cut skill consumes application-independent inputs only. It does not
read or write a Jianying project and does not call `jianying-editor`. If the
current subtitle state must be obtained from an encrypted draft, stop at this
boundary and request an explicit read-only project probe outside this skill.

## Inputs and order

1. Establish the edited-timeline audio and subtitle-state evidence as
   application-independent inputs. A missing or unreadable subtitle state is
   unknown, not proof that the timeline has no subtitles.
2. For `existing`, read the current visible subtitle text, order, segmentation,
   and saved ranges; compare them with the actual speech. Do not rebuild them
   from ASR or an older subtitle copy.
3. For `generate`, require timed `segment`/`word` transcript evidence. Correct
   names, terms, numbers, units, models, negation, conditions, causality, and
   semantic segmentation without changing token or segment timestamps.
4. Use the saved edited audio's waveform evidence to locate candidate
   boundaries; ordinary ASR timing is not a final boundary source.
5. Review the complete subtitle list in context, then output an
   application-independent `subtitle_alignment_plan`; generated runs may also
   output an UTF-8 SRT for preview.
6. Keep `review_status=pending` until human listening and plan approval. Any
   later project read/write or application handoff is outside this skill's
   execution boundary.

If a later rough-cut change changes source order, source range, speed, or duration, repeat this stage. A packaging-only style change does not require full re-alignment unless it changes subtitle timing or segmentation.

## Existing-timeline anchor units, not seconds

For the existing-timeline/token-map path, a subtitle screen stores a list of stable word/semantic-unit references plus the display text — **not** absolute seconds. Post-cut time is *computed* each pass from (token time in the source) + (which ranges the edit list kept):

- token's source time → already in the time-coded transcript;
- which segments survive → in the content decision plan / edit list;
- token's edited-timeline time → arithmetic of the two, with no approximation.

Do not re-run ASR on the edited video to recover timing: it re-listens to the same speech, costs time, and forces every proper noun to be re-corrected. Do not stitch the **original** subtitle cues head-to-tail along the edit list either — those cue boundaries were cut on the original's pauses, so pasted after an edit they drift further and further off. Only the per-token mapping survives editing intact.

Subtitles may legitimately differ in text from the transcript (punctuation, removed fillers, official spellings); that divergence is intentional. The transcript answers "what was said"; the subtitle answers "what the viewer reads".

The no-subtitle generation path has no Jianying token IDs. It uses the supplied
timed transcript segments/words as semantic units, preserves their timestamps
during dictionary correction, and emits a pending waveform candidate plan plus
an optional SRT preview.

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

Word-level timestamps are a cross-check only for `existing`. In `generate`,
timed transcript tokens are required to construct the semantic units, but the
waveform still controls boundary candidates and review. If timing health fails
or text and timing disagree, block generation or fall back to manual evidence;
do not silently treat plain text as timed input. The fixed script routes are
`subtitle-align` for existing subtitles and `subtitle-generate` for no-subtitle
generation. Both emit review-pending plans and do not write the draft.

## Deprecated practices

Recognize and reject these obsolete patterns; do not reintroduce them.

- **Overwriting existing subtitles without asking.** A rebuild replaces the screens, wording, and breaks a human already tuned — and nothing downstream can recover them. Editing a few characters is not a rebuild: change those units in place. A full overwrite is the one operation in this stage that requires explicit confirmation first.
- **Re-running ASR on the edited video to recover timing.** Obsolete. Post-cut time is computed from token source-times plus the kept ranges ([Anchor units, not seconds](#anchor-units-not-seconds)); a second transcription only re-hears the same speech and forces every proper noun to be re-corrected.
- **Stitching the original subtitle cues head-to-tail along the edit list.** Those cue boundaries were cut on the original's pauses and drift after an edit. Only the per-token/semantic-unit mapping survives.
- **Keeping ASR cue boundaries as subtitle screens.** Segment by the punctuation ladder above, not by whatever breaks the recognizer happened to emit.
- **Treating the subtitle stage as a fixed pipeline step.** It is a standalone operation: run it whenever the account ledger (decision plan / edit list) and time-coded transcript exist, and re-run it after any change that moves, deletes, or re-times surviving speech.
