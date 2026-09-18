# Subtitle alignment plan contract

Validate with:

```powershell
python scripts/validate_alignment_plan.py <alignment-plan.json>
```

The plan is application-independent. It may contain semantic unit IDs, corrected text, microsecond ranges, audio/picture/manual boundary choices, evidence, confidence, and review status. It must not contain Jianying track IDs, segment IDs, material IDs, draft paths, replica paths, encryption fields, or JSON write instructions.

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
  "review": {"status": "draft"},
  "recheck_if": ["rough-cut changes source order or duration"]
}
```
