import copy
import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "validate_plan.py"
SPEC = importlib.util.spec_from_file_location("validate_plan", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load {SCRIPT}")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
validate = MODULE.validate
main = MODULE.main


class PlanTests(unittest.TestCase):
    def base(self):
        return {
            "version": 1,
            "input": {
                "timebase": "seconds",
                "duration": 10.0,
                "completeness": {
                    "status": "complete",
                    "checked": ["video", "audio", "transcript"],
                    "missing": [],
                    "evidence": ["full source playback and transcript inventory"],
                    "impact": "none",
                },
            },
            "evidence": [{"kind": "transcript"}],
            "goal": {"type": "content_cleanup"},
            "theme_analysis": {
                "topic": "A discussion topic",
                "thesis": "The central proposition",
                "purpose": "discussion",
                "audience": "general audience",
                "confidence": "high",
            },
            "domain_analysis": {
                "status": "identified",
                "primary_domain": "general",
                "confidence": "high",
                "segments": [],
                "terms": [],
                "entities": [],
                "protected_facts": [],
                "unresolved_terms": [],
            },
            "outline": {
                "confidence": "high",
                "units": [{
                    "id": "U1", "title": "Opening", "role": "setup",
                    "start": 0.0, "end": 1.0, "timebase": "seconds", "confidence": "high",
                }],
            },
            "speakers": [{"id": "A", "role": "host", "confidence": "high"}],
            "original_structure": [],
            "recommended_structure": [],
            "protected_facts": [],
            "workflow": {"content_pass": "stable", "refinement_pass": "not_started"},
            "decisions": [{
                "id": "D1", "pass": "content", "action": "keep", "confidence": "high",
                "start": 0.0, "end": 1.0, "timebase": "seconds", "summary": "Keep opening",
                "reason": "Establishes context", "flags": [], "domain_sensitive": False,
                "boundary": {
                    "start_basis": "sentence_boundary",
                    "end_basis": "sentence_boundary",
                    "evidence": ["transcript", "audio"],
                    "precision": "exact",
                },
            }],
        }

    def test_valid_independent_plan(self):
        self.assertTrue(validate(self.base())["ok"])

    def test_orientation_is_required(self):
        plan = self.base()
        del plan["domain_analysis"]
        self.assertFalse(validate(plan)["ok"])

    def test_review_decision_is_allowed(self):
        plan = self.base()
        plan["decisions"][0].update({
            "action": "review", "confidence": "low", "flags": ["needs_listen"],
        })
        self.assertTrue(validate(plan)["ok"])

    def test_unresolved_domain_blocks_high_confidence_destructive_cut(self):
        plan = self.base()
        plan["domain_analysis"].update({"status": "uncertain", "confidence": "low"})
        plan["decisions"][0].update({
            "action": "delete", "domain_sensitive": True, "expected_join": "Next sentence continues the point",
        })
        self.assertFalse(validate(plan)["ok"])

    def test_unresolved_domain_cut_requires_review_marker(self):
        plan = self.base()
        plan["domain_analysis"].update({"status": "uncertain", "confidence": "low"})
        plan["decisions"][0].update({
            "action": "shorten", "confidence": "medium", "domain_sensitive": True,
            "flags": ["needs_context"], "expected_join": "The qualified answer remains connected",
        })
        self.assertTrue(validate(plan)["ok"])

    def test_multi_domain_outline_is_supported(self):
        plan = self.base()
        plan["domain_analysis"].update({
            "status": "identified",
            "primary_domain": "technology and business",
            "segments": [
                {"start": 0.0, "end": 0.5, "domain": "technology", "confidence": "high"},
                {"start": 0.5, "end": 1.0, "domain": "business", "confidence": "medium"},
            ],
            "terms": ["API", "market fit"],
            "unresolved_terms": ["ambiguous acronym"],
        })
        plan["outline"]["units"].append({
            "id": "U2", "title": "Business implication", "role": "explanation",
            "start": 1.0, "end": 2.0, "timebase": "seconds", "confidence": "medium",
        })
        self.assertTrue(validate(plan)["ok"])

    def test_timebase_and_duration_are_checked(self):
        plan = self.base()
        plan["decisions"][0]["timebase"] = "frames"
        self.assertFalse(validate(plan)["ok"])
        plan = self.base()
        plan["decisions"][0]["end"] = 11.0
        self.assertFalse(validate(plan)["ok"])

    def test_application_handoff_is_rejected(self):
        plan = self.base()
        plan["execution_handoff"] = {"keep_blocks": []}
        self.assertFalse(validate(plan)["ok"])

    def test_completeness_blocks_high_confidence_destructive_decision(self):
        plan = self.base()
        plan["input"]["completeness"] = {
            "status": "partial",
            "checked": ["video", "audio"],
            "missing": ["transcript"],
            "evidence": ["ASR file was not supplied"],
            "impact": "review_required",
        }
        plan["decisions"][0].update({
            "action": "delete",
            "expected_join": "The next sentence continues the explanation",
        })
        self.assertFalse(validate(plan)["ok"])

    def test_approximate_destructive_boundary_requires_review(self):
        plan = self.base()
        plan["decisions"][0].update({
            "action": "shorten",
            "confidence": "medium",
            "flags": ["human_review"],
            "expected_join": "The sentence remains grammatical after the pause",
            "boundary": {
                "start_basis": "phrase_boundary",
                "end_basis": "pause",
                "evidence": ["waveform"],
                "precision": "approximate",
            },
        })
        result = validate(plan)
        self.assertTrue(result["ok"])

    def test_refinement_requires_stable_content_pass(self):
        plan = self.base()
        plan["workflow"] = {"content_pass": "draft", "refinement_pass": "draft"}
        plan["decisions"][0]["pass"] = "refinement"
        self.assertFalse(validate(plan)["ok"])

    def test_refinement_is_allowed_after_content_pass_is_stable(self):
        plan = self.base()
        plan["workflow"] = {"content_pass": "stable", "refinement_pass": "draft"}
        plan["decisions"][0]["pass"] = "refinement"
        self.assertTrue(validate(plan)["ok"])

    def test_boundary_is_required(self):
        plan = self.base()
        del plan["decisions"][0]["boundary"]
        self.assertFalse(validate(plan)["ok"])

    def test_subtitle_alignment_status_is_gated_by_content_pass(self):
        plan = self.base()
        plan["workflow"]["subtitle_alignment"] = "approved"
        self.assertTrue(validate(plan)["ok"])
        plan["workflow"] = {
            "content_pass": "draft",
            "refinement_pass": "not_started",
            "subtitle_alignment": "approved",
        }
        self.assertFalse(validate(plan)["ok"])

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

        plan = self.base()
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "plan.json"
            path.write_text(_json.dumps(plan, ensure_ascii=False), encoding="utf-8")
            argv_backup = sys.argv
            try:
                sys.argv = ["validate_plan.py", str(path)]
                rc = main()
            finally:
                sys.argv = argv_backup
        self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()
