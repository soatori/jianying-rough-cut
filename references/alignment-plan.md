# Subtitle alignment plan contract

Validate with:

```powershell
python scripts/roughcut_tool.py validate alignment <alignment-plan.json>
```

The plan is application-independent. It may contain semantic unit IDs, corrected text, microsecond ranges, audio/picture/manual boundary choices, evidence, confidence, and review status. It must not contain Jianying track IDs, segment IDs, material IDs, draft paths, replica paths, encryption fields, or JSON write instructions.

For the two subtitle paths, `source.text_authority` and
`source.subtitle_origin` make the input contract explicit. Existing subtitles
use `text_authority: "current_visible_subtitle"` and
`subtitle_origin: "current_timeline"`; generated subtitles use
`text_authority: "generated_transcript"` and
`subtitle_origin: "generated_transcript"`. In the existing path, ASR can only
be cross-check evidence. In the generated path, dictionary corrections may
change text but not the timed tokens or semantic-unit times. An SRT exported
from the final plan is a UTF-8 review artifact and is not an application write
source.

When edited-audio evidence is available, record the exact artifact identity in `source.evidence` using `content_hash`, `duration_us`, `sample_rate`, `channels`, and `codec` rather than relying on a filename alone. Any playback-order, speed, volume, duration, or stream-format change invalidates the prior plan and requires regeneration. A unit may carry `repeat_intent: {"intentional": true, "evidence": "..."}` to exempt an otherwise identical adjacent text warning.

For a read-only final-draft audit, add `mode: "final_draft_audit"` and set `source.text_authority` to `final_visible_subtitle`. ASR and older subtitle text remain evidence only. Add `source.subtitle_reference` with an ID, hash, and approved/stable status. If source and target order differs, add `comparison` with order hashes, semantic-unit sequences, a mapping list, and `remap_status`; approved output requires `not_required` or `verified`.

Minimal shape:

```json
{
  "schema_version": 1,
  "plan_type": "subtitle_alignment_plan",
  "source": {
    "content_plan_id": "content-v1",
    "content_plan_hash": "sha256:...",
    "timebase": "microseconds",
    "duration_us": 12000000,
    "text_authority": "current_visible_subtitle",
    "subtitle_origin": "current_timeline",
    "evidence": [{"kind": "edited_audio", "status": "available"}]
  },
  "policy": {
    "mode": "hybrid",
    "default_boundary_mode": "audio",
    "tolerance_us": 40000,
    "detector": {
      "hop_us": 10000,
      "window_us": 25000,
      "pause_min_us": 120000,
      "pause_cap_us": 350000
    },
    "words_health": {"status": "valid", "role": "cross_check"}
  },
  "subtitle_units": [],
  "review": {"status": "pending"},
  "recheck_if": ["rough-cut changes source order or duration"]
}
```

The existing-subtitle token-map helper remains chained from the canonical playback map:

```text
playback-map -> scan -> build-alignment -> validate alignment
```

`build-alignment` requires verified token mapping and canonical `units`; it calculates every new `start_us/end_us` from edited token times. Any old subtitle `start_us/end_us` is retained only under evidence such as `previous_range`, never copied to the new cue. Each unit has a stable `id`, `semantic_unit_id`, `review_status: "pending"`, and token-mapping evidence; boundaries use validator-supported `basis: "word_boundary"` and `review: "pending"`. Missing tokens, duplicate semantic IDs, non-contiguous mapped intervals, unresolved remaps, or missing duration/evidence block the generated report, which is self-checked by the alignment validator.

To recheck a saved plan against the current edited audio, use:

```powershell
python scripts/roughcut_tool.py validate alignment <plan.json> --audio <current-audio>
```

A mismatch in any identity field blocks validation.

The no-subtitle route is separate and does not require Jianying token IDs:

```text
timed-transcript -> dictionary text correction -> subtitle-generate units
                 -> one waveform pass -> subtitle_alignment_plan -> UTF-8 SRT preview
```

The supplied segment/word timestamps seed the generated units, while waveform
evidence supplies boundary candidates and human review remains pending.

Subtitle units must remain in playback order with non-decreasing `start_us` and
`end_us`. The plan validator and SRT renderer reject a later unit whose end
time moves backward, even when each individual range is valid.

Subtitle units are semantic screens, not clones of picture segments. A unit may
cross material cuts. In a material-boundary review, check only each unit's
outer start/end against the allowed boundary set and report internal crossings
separately. Do not create an identical adjacent unit solely because the picture
cut; flag duplicate text for review unless repeated speech or reading cadence
makes the repetition intentional.
