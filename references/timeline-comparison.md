# Timeline comparison and semantic remapping

Use this reference when comparing the raw timeline, rough cut, selected-phrase timeline, packaging timeline, or final timeline.

## Adjacency is playable, not file order

Whether two lines are "the same idea twice" depends on them being **adjacent as played**, not adjacent as stored. In an edited timeline, two source sentences 40s apart can sit shoulder to shoulder, and two source-adjacent sentences may still have kept material between them. Always build the judgment view by flattening in **playback order from the edit list** (segment sequence + source ranges + kept/removed), then remap to stable semantic-unit IDs.

Two silent failure modes come from hand-reconstructing this view from raw segment files instead:

- **Gap numbering read as hidden content.** Grouping by original paragraph numbers leaves jump-cuts in the numbering; a gap is misread as "there is a span I was not shown, so I cannot judge", and correct deletions get vetoed — while that "missing" span is exactly the already-removed audio.
- **Suppressed pauses mislabeled as removed speech.** Marking every tightened pause as "content was deleted here" inflates the removal markers many-fold, the reader believes the piece is broken apart everywhere, and judgment collapses into blanket conservatism (prefer not to cut).

Both share one root: the criterion was fine, but the *input lied, silently*. The view format changes the conclusion, not just the presentation. When a downstream change reorders or re-times, remap by semantic-unit ID and context before reusing any old timecode; never reuse the raw file order as a proxy for what the viewer hears.

## Comparison order

1. Compare the ordered source video/audio segment sequence.
2. Compare semantic-unit sequence and group membership.
3. Compare subtitle text authority and visible wording.
4. Classify each change as `copied`, `shortened`, `deleted`, `reordered`, `packaged`, or `appended_media`.
5. Only then compare time ranges and visual/audio layers.

Subtitle rows and old effect timestamps are not stable identifiers. A changed order or duration invalidates direct reuse of an old timecode.

## Remapping contract

Each mapped unit uses a stable semantic-unit ID plus a final-subtitle reference. Record source and target order fingerprints and one mapping entry for each affected unit. Allowed mapping states are:

- `not_required`: order and membership are unchanged;
- `pending`: evidence exists but mapping is incomplete;
- `verified`: mapping was checked against final subtitles and context;
- `blocked`: the unit cannot be safely mapped.

Packaging may receive only `not_required` or `verified` mappings for a final plan. `pending` and `blocked` are report states, not execution permission.

## Audit-only boundary

This comparison produces evidence and discrepancy reports. It does not move, delete, rewrite, or write back a draft. If a mismatch is found, return the semantic decision to the appropriate upstream stage and keep the mismatch reviewable.
