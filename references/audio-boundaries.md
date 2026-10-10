# Audio, waveform, pauses, and cut boundaries

## Evidence hierarchy

Use waveform and silence detection to locate candidates. Use actual listening plus semantics to decide. A low-amplitude region can be a breath, room tone, trailing consonant, overlap, or edit damage; duration alone does not identify its function.

## Pause classes

Use exactly these labels after contextual review:

| Label | Context to review |
| --- | --- |
| `hesitation` | Sentence-internal search or uncertainty |
| `sentence_boundary` | End of a complete sentence and its phrasing |
| `speaker_handoff` | Speaker change, response timing, or overlap |
| `topic_shift` | Transition between ideas and required setup |
| `emphasis` | Deliberate space around a stressed point |
| `emotional_beat` | Emotion, reaction, or expressive silence |
| `breath` | Audible inhalation/exhalation and articulation |
| `failed_take_gap` | Gap between abandoned and restarted attempts |
| `edit_damage` | Abnormal gap caused by an earlier edit |

These are functions, not duration buckets. None inherently authorizes removal.
Review phrasing, speakers, surrounding semantic units, and source/edit history.
Keep `pause_function: unavailable` when required context is missing;
`not_assessed` is reserved for out-of-scope assessment. A decision that supplies
a functional label must include nonempty `pause_context_evidence` strings.

The pause scanner emits `duration_us` separately from `pause_function`, which
always starts as `unavailable`, even if precomputed waveform input carries a
label. Its rows have `action: review`, `candidate_only: true`,
`contextual_review_required: true`, `provenance: script_generated`,
`human_review: true`, and `human_listening: pending`. The report's
`pause_function_options` lists the taxonomy without selecting a function.
`pause_min_us` only selects intervals meeting a duration threshold. Detector
output config includes only `pause_min_us` and `noise_db`. Shared waveform
settings (`pause_cap_us`, `edge_window_us`, `tolerance_us`, `hop_us`, `window_us`,
`auto_snap_within_tolerance`) are accepted for workflow compatibility but ignored
by this detector and omitted from its output. Other settings are rejected so
automatic action instructions cannot be echoed into candidate output.

Default to compression rather than removal. Preserve enough room for articulation and speaker change. Topic shifts, contrast, emotion, and emphasis may need more time than ordinary sentence boundaries.

Any numerical threshold is a configurable detector, not a deletion rule. Calibrate it to speaking rate, language, recording noise, platform rhythm, and the requested style.

Compression is a planning preference after context review, not a scanner action.
If a proposed pause change alters semantic membership, order, or protected-fact
meaning, set `escalate_to_rough_cut: true` and `human_review: true` and return it
to the content pass. Nonsemantic local cleanup may remain refinement work.
Never clear `human_listening` from duration, a functional label, or agent playback.

## Boundary checks

For each proposed local cut:

- listen before, across, and after the join;
- avoid clipping plosives, fricatives, vowels, word-final consonants, laughter, and breaths that carry phrasing;
- inspect room-tone and noise-floor discontinuities;
- check whether two speakers overlap;
- preserve sync when picture is tied to production audio;
- flag clicks, abrupt ambience changes, or unnaturally accelerated delivery.

## Already-edited material

Distinguish source defects from edit defects. Look for tiny residual syllables, duplicate frames of speech, reversed source order, missing setup, abrupt room-tone changes, and over-tightened speaker handoffs. Compare against the source or an earlier cut when available.

