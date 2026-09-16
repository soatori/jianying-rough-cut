# DONE — 2026-09-16 review-fixes

Plan: `docs/superpowers/plans/2026-09-16-review-fixes.md`

## Commits

| Commit | Task |
|--------|------|
| `11c7f68` | Task 1 — description rewrite (Use when + 中文触发 + Do NOT) |
| `c12bceb` | Task 2 — structured `mode == "manual"` warning + 3 alignment tests |
| `1d6d4d6` | Task 3 — duplicate id / duration / words_health / CLI smoke tests |
| `c4f9708` | Task 4 — Decision rules compress (~100 words, hard rules kept) |
| `0b34149` | Task 5 — unify importlib loader in `test_validate_plan.py` |

## Done criteria

- [x] Description has Use when + 粗剪/口播/字幕校对 + negatives (415 chars ≤ 1024)
- [x] Manual warning is structural (`mode == "manual"`), not substring
- [x] New tests cover duplicate id / duration / manual warning / CLI smoke / words_health
- [x] Full `unittest discover -s tests` is green: **28 OK** (was 20)
- [x] Zero files deleted (`agents/openai.yaml` retained)

## Notes

- Task 2 duration bound already existed at `validate_alignment_plan.py:198-199`; `test_end_us_beyond_duration_rejected` is regression coverage only.
- Task 3 `role=fallback` requires `status != "valid"` (valid timing is cross_check-only). Test uses `status=unavailable` + `role=fallback`.
- Task 4 reduced Decision rules by ~100 words (1441 → 1341). Hard rules kept verbatim: no fragment stitch, approximate+high-confidence destructive forbidden, partial/unknown gate, domain-sensitive recording, waveform never authorizes deletion alone. Two-pass phase language and `recheck_if` untouched.
- Cleared 2026-09-16: deleted `agents/openai.yaml` (commit `a55d416`).
- Still deferred: extract shared validator helpers, rationalization table.
- Post-clear: unittest 28 OK; validate_skill PASS 0 errors / 0 warnings.
