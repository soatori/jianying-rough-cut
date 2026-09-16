# jianying-rough-cut Review Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix P0–P3 review findings without deleting files — rewrite description for WHEN + Chinese triggers, fix the brittle `"manual" in str(...)` warning, add missing unit tests, and lightly compress SKILL.md Decision rules overlap.

**Architecture:** Frontmatter rewrite on `SKILL.md`; one structural predicate in `scripts/validate_alignment_plan.py`; four new unittest cases split across the two existing test files; optional word trim in Decision rules. No architecture change, no file removal.

**Tech Stack:** Markdown, Python 3 stdlib (`unittest`, `importlib.util`)

**Spec:** `C:\Users\cbsjz\Desktop\skills\jianying-rough-cut\REVIEW.md` (sections 1.4, 3, 4, 6)

## Global Constraints

- **No file deletions.** `agents/openai.yaml` stays; deferred at end.
- Do not weaken domain-unresolved / material-incomplete / phase gates or `REJECTED_FIELDS` application-field rejection.
- tests/ must remain offline, no network, no Jianying binary dependency.
- Every validator change must keep existing 20 tests green and add the new ones below.
- Description: Use when… + Chinese literal phrases + negative triggers, <1024 chars.

## File Map

| File | Change |
|------|--------|
| `SKILL.md` | Rewrite description; optional Decision rules compress |
| `scripts/validate_alignment_plan.py:235-237` | Structural manual-boundary detection |
| `tests/test_validate_alignment_plan.py` | Add manual-mode warning + duration overrun tests |
| `tests/test_validate_plan.py` | Add duplicate id + words_health + CLI smoke tests |

---

### Task 1: Rewrite rough-cut description (SDO)

**Files:**
- Modify: `SKILL.md:1-4` (frontmatter)

**Interfaces:**
- Produces: new `description` for discovery

- [ ] **Step 1: Replace description**

```yaml
description: Use when rough-cutting speech-led video/audio (口播/访谈/教程/讲座) — decide semantic keep/delete/shorten/reorder before touching a project file, or proofread subtitles against edited audio. Triggers: rough cut, 粗剪, semantic cut, content pass vs refinement, subtitle alignment, 字幕校对/对齐, speech cleanup, 去口水音. Do NOT use to edit CapCut/Jianying project files, package effects (花字/卡点), or cut non-speech montage.
```

- [ ] **Step 2: Verify length and keywords**

```powershell
$line = (Select-String -Path SKILL.md -Pattern '^description:').Line
$line.Length  # must be <= 1024
$line -match 'Use when' -and $line -match '粗剪' -and $line -match 'Do NOT'
```

Expected: True / True / True.

- [ ] **Step 3: Commit**

```bash
git add SKILL.md
git commit -m "fix(rough-cut): rewrite description with WHEN and Chinese triggers"
```

---

### Task 2: Fix brittle manual-boundary warning (TDD)

**Files:**
- Modify: `tests/test_validate_alignment_plan.py`
- Modify: `scripts/validate_alignment_plan.py:235-237`

**Interfaces:**
- Consumes: `valid_plan()` fixture in the alignment test module
- Produces: warning fires only when a boundary `mode == "manual"` (structured), not when evidence text merely contains the substring "manual"

- [ ] **Step 1: Write failing tests**

Append to `class AlignmentPlanTests` in `tests/test_validate_alignment_plan.py`:

```python
    def test_approved_manual_mode_emits_audit_warning(self):
        plan = valid_plan()
        plan["subtitle_units"][0]["boundaries"]["start"].update({
            "mode": "manual",
            "basis": "manual_marker",
            "evidence": ["edited_audio"],
            "confidence": "high",
            "review": "approved",
        })
        result = MODULE.validate(plan)
        self.assertTrue(result["ok"], result)
        self.assertTrue(
            any("manually resolved" in w for w in result.get("warnings", [])),
            result,
        )

    def test_evidence_text_containing_manual_does_not_warn(self):
        plan = valid_plan()
        # valid_plan start is already mode=audio, review=approved
        plan["subtitle_units"][0]["boundaries"]["start"]["evidence"] = [
            "edited_audio",
            "manual_marker_note_only",
        ]
        result = MODULE.validate(plan)
        self.assertTrue(result["ok"], result)
        self.assertFalse(
            any("manually resolved" in w for w in result.get("warnings", [])),
            result,
        )

    def test_end_us_beyond_duration_rejected(self):
        plan = valid_plan()
        plan["subtitle_units"][0]["end_us"] = 50_000_000  # duration_us is 10_000_000
        self.assertFalse(MODULE.validate(plan)["ok"])
```

Note: if `end_us` beyond duration is **already** rejected by existing code, `test_end_us_beyond_duration_rejected` will pass immediately — keep it as regression coverage. If the validator does **not** reject it, implement that check in Step 3 as a positive integer bound (`end_us > duration_us` → error).

- [ ] **Step 2: Run — expect FAIL on warning tests**

```powershell
Set-Location C:\Users\cbsjz\Desktop\skills\jianying-rough-cut
& $env:MIMO_PYTHON -m unittest tests.test_validate_alignment_plan -v
```

Expected: `test_evidence_text_containing_manual_does_not_warn` FAILS (false positive warning). `test_approved_manual_mode_emits_audit_warning` may PASS accidentally via substring — after Step 3 both must pass for the right reason.

- [ ] **Step 3: Implement structured check**

Replace lines ~235-237:

```python
    if plan.get("review", {}).get("status") == "approved" if isinstance(plan.get("review"), dict) else False:
        if any("manual" in str(unit.get("boundaries", {})) for unit in units if isinstance(unit, dict)):
            warnings.append("approved plan contains manually resolved boundaries; retain the evidence for audit")
```

with:

```python
    review_obj = plan.get("review") if isinstance(plan.get("review"), dict) else {}
    if review_obj.get("status") == "approved":
        def _has_manual_mode(boundaries: object) -> bool:
            if not isinstance(boundaries, dict):
                return False
            for end in ("start", "end"):
                edge = boundaries.get(end)
                if isinstance(edge, dict) and edge.get("mode") == "manual":
                    return True
            return False

        if any(_has_manual_mode(unit.get("boundaries")) for unit in units if isinstance(unit, dict)):
            warnings.append("approved plan contains manually resolved boundaries; retain the evidence for audit")
```

If Step 1 revealed missing duration bound, also add near start/end numeric checks:

```python
        end_us = unit.get("end_us")
        duration_us = source.get("duration_us") if isinstance(source, dict) else None
        if is_int(end_us) and is_int(duration_us) and end_us > duration_us:
            errors.append(f"{path}.end_us: exceeds source.duration_us")
```

(Use the module's existing `is_int` / path conventions — match neighboring code exactly.)

- [ ] **Step 4: Full rough-cut test suite**

```powershell
& $env:MIMO_PYTHON -m unittest discover -s tests -v
```

Expected: all OK (previous 20 + new cases).

- [ ] **Step 5: Commit**

```bash
git add scripts/validate_alignment_plan.py tests/test_validate_alignment_plan.py
git commit -m "fix(rough-cut): structured manual-boundary warning + duration bound tests"
```

---

### Task 3: Fill validate_plan.py coverage gaps

**Files:**
- Modify: `tests/test_validate_plan.py`
- Modify: `tests/test_validate_alignment_plan.py` (words_health — alignment plan owns that field)

**Interfaces:**
- Consumes: `PlanTests.base()` fixture; `validate` imported as `from validate_plan import validate`; CLI `main()` via `argparse` with positional `plan` path
- Produces: tests only — **do not change** `scripts/validate_plan.py` (duplicate-id rejection already exists at lines 313–319; duration bound already exists in `_validate_range`)

**Facts from current code (do not re-invent schema):**
- Content plan fixture: `decisions[].id`, `input.duration` (seconds), `outline.units[].end`
- Duplicate id: already errors when `decision_id in ids`
- Duration overrun: `_validate_range` errors when `end > duration`
- `words_health` lives on **alignment** plan `policy.words_health` (`status` + `role` in `{"cross_check","fallback"}`)
- CLI: `validate_plan.py` exposes `main()` using `argparse` + `sys.argv`

- [ ] **Step 1: Add content-plan tests**

Append to `class PlanTests` in `tests/test_validate_plan.py` (add `import copy` and `import json` and `import tempfile` at top if missing):

```python
    def test_duplicate_decision_ids_rejected(self):
        plan = self.base()
        plan["decisions"].append(copy.deepcopy(plan["decisions"][0]))
        result = validate(plan)
        self.assertFalse(result["ok"])
        self.assertTrue(any("duplicates id" in e for e in result["errors"]), result["errors"])

    def test_outline_end_exceeds_duration_rejected(self):
        plan = self.base()
        plan["outline"]["units"][0]["end"] = 99.0  # input.duration is 10.0
        self.assertFalse(validate(plan)["ok"])

    def test_cli_main_smoke(self):
        import json as _json
        import sys
        import tempfile
        from pathlib import Path
        from validate_plan import main as plan_main

        plan = self.base()
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "plan.json"
            path.write_text(_json.dumps(plan, ensure_ascii=False), encoding="utf-8")
            argv_backup = sys.argv
            try:
                sys.argv = ["validate_plan.py", str(path)]
                rc = plan_main()
            finally:
                sys.argv = argv_backup
        self.assertEqual(rc, 0)
```

- [ ] **Step 2: Add words_health tests to alignment suite**

Append to `class AlignmentPlanTests` in `tests/test_validate_alignment_plan.py`:

```python
    def test_words_health_role_must_be_valid(self):
        plan = valid_plan()
        plan["policy"]["words_health"]["role"] = "authoritative"
        self.assertFalse(MODULE.validate(plan)["ok"])

    def test_words_health_role_fallback_allowed(self):
        plan = valid_plan()
        plan["policy"]["words_health"]["role"] = "fallback"
        self.assertTrue(MODULE.validate(plan)["ok"], MODULE.validate(plan))
```

If Step 2 fails because `role=fallback` is rejected for another reason, inspect `validate_alignment_plan.py` lines 160–167 and keep the test asserting the **documented** enum only.

- [ ] **Step 3: Run full suite — expect PASS (no production change)**

```powershell
Set-Location C:\Users\cbsjz\Desktop\skills\jianying-rough-cut
& $env:MIMO_PYTHON -m unittest discover -s tests -v
```

Expected: all OK (previous 20 + 5 new). If a new test fails, the production code is wrong for that case — fix the **test expectation** only if REVIEW overstated the gap; otherwise stop and report.

- [ ] **Step 4: Commit**

```bash
git add tests/test_validate_plan.py tests/test_validate_alignment_plan.py
git commit -m "test(rough-cut): cover duplicate ids, duration bound, words_health, CLI smoke"
```

---

### Task 4: Compress Decision rules overlap (optional, P3)

**Files:**
- Modify: `SKILL.md` Decision rules section (~lines 74–92)

**Interfaces:**
- Produces: ~150–250 fewer words; references remain authoritative for deep criteria

- [ ] **Step 1: Measure before**

```powershell
(Get-Content SKILL.md | Measure-Object -Word).Words
```

- [ ] **Step 2: Compress without losing hard rules**

Keep **verbatim** (non-negotiable):
- Do not stitch unfinished fragments
- Approximate + high-confidence destructive → forbidden
- Material partial/unknown → no high-confidence delete/shorten/reorder/join
- Domain-sensitive facts must be recorded
- Waveform thresholds never authorize deletion alone

Merge soft/redundant bullets (e.g. multiple boundary-evidence enumerations) into one bullet that points to `references/content-analysis.md` / `references/audio-boundaries.md` for full criteria.

Do **not** remove two-pass phase language or `recheck_if` requirements.

- [ ] **Step 3: Measure after**

Expected: reduction of ~150–250 words; still >1100 total is OK if hard rules intact.

- [ ] **Step 4: Commit**

```bash
git add SKILL.md
git commit -m "docs(rough-cut): compress Decision rules overlap with references"
```

---

### Task 5: Import style consistency (P3)

**Files:**
- Modify: `tests/test_validate_plan.py` and/or `tests/test_validate_alignment_plan.py`

**Interfaces:**
- Produces: both tests load validators the same way

- [ ] **Step 1: Pick one loader**

Prefer the `importlib.util.spec_from_file_location` pattern already used by `test_validate_alignment_plan.py` (more explicit on Windows).

- [ ] **Step 2: Rewrite the other file's loader**

If `test_validate_plan.py` uses `sys.path.insert`, replace with:

```python
import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "validate_plan.py"
SPEC = importlib.util.spec_from_file_location("validate_plan", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load {SCRIPT}")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
```

Update all `validate(...)` call sites to `MODULE.validate(...)` if needed.

- [ ] **Step 3: Run suite**

```powershell
& $env:MIMO_PYTHON -m unittest discover -s tests -v
```

Expected: all OK.

- [ ] **Step 4: Commit**

```bash
git add tests
git commit -m "test(rough-cut): unify importlib loader style"
```

---

## Deferred (NOT in this plan — 先不删除)

1. Delete `agents/openai.yaml` after confirming MiMo/host does not require it
2. Extract shared helpers between the two validators (optional; self-contained files may be intentional)
3. Add rationalization/red-flags table for discipline rules (nice-to-have, not blocking)

## Done criteria

- [ ] Description has Use when + 粗剪/口播/字幕校对 + negatives
- [ ] Manual warning is structural (`mode == "manual"`), not substring
- [ ] New tests cover duplicate id / duration / manual warning / CLI (or skipTest with reason)
- [ ] Full unittest discover is green
- [ ] Zero files deleted
