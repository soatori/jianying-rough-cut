# Subtitle alignment plan contract

Validate with:

```powershell
python scripts/validate_alignment_plan.py <alignment-plan.json>
```

The plan is application-independent. It may contain semantic unit IDs, corrected text, microsecond ranges, audio/picture/manual boundary choices, evidence, confidence, and review status. It must not contain Jianying track IDs, segment IDs, material IDs, draft paths, replica paths, encryption fields, or JSON write instructions.

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
