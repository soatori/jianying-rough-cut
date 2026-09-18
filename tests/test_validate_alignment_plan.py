import copy
import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "validate_alignment_plan.py"
SPEC = importlib.util.spec_from_file_location("validate_alignment_plan", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load {SCRIPT}")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def valid_plan():
    return {
        "schema_version": 1,
        "plan_type": "subtitle_alignment_plan",
        "source": {
            "content_plan_id": "content-v1",
            "content_plan_hash": "sha256:content",
            "timebase": "microseconds",
            "duration_us": 10_000_000,
            "evidence": [{"kind": "edited_audio", "status": "available"}],
        },
        "policy": {
            "mode": "hybrid",
            "default_boundary_mode": "audio",
            "tolerance_us": 40_000,
            "detector": {
                "hop_us": 10_000,
                "window_us": 25_000,
                "pause_min_us": 120_000,
                "pause_cap_us": 350_000,
            },
            "words_health": {"status": "valid", "role": "cross_check"},
        },
        "subtitle_units": [{
            "id": "S1",
            "semantic_unit_id": "U1",
            "source_text": "这是一个识别结果",
            "text": "这是一个校正结果",
            "start_us": 0,
            "end_us": 2_000_000,
            "boundaries": {
                "start": {
                    "mode": "audio", "basis": "phrase_boundary",
                    "evidence": ["edited_audio", "transcript"],
                    "confidence": "high", "review": "approved",
                },
                "end": {
                    "mode": "picture", "basis": "shot_boundary",
                    "evidence": ["shot_03", "pause"],
                    "confidence": "medium", "review": "approved",
                },
            },
            "review_status": "approved",
            "corrections": [{"kind": "asr_term", "reason": "listen-back correction"}],
        }],
        "review": {"status": "approved"},
        "recheck_if": ["rough-cut changes source order or duration"],
    }


class AlignmentPlanTests(unittest.TestCase):
    def test_valid_hybrid_plan(self):
        result = MODULE.validate(valid_plan())
        self.assertTrue(result["ok"], result)

    def test_picture_boundary_requires_picture_evidence(self):
        plan = valid_plan()
        plan["subtitle_units"][0]["boundaries"]["end"].update({
            "basis": "waveform",
        })
        self.assertFalse(MODULE.validate(plan)["ok"])

    def test_manual_boundary_requires_review(self):
        plan = valid_plan()
        plan["subtitle_units"][0]["boundaries"]["start"].update({
            "mode": "manual", "review": "pending",
        })
        self.assertFalse(MODULE.validate(plan)["ok"])

    def test_application_fields_are_rejected(self):
        plan = valid_plan()
        plan["subtitle_units"][0]["segment_id"] = "jianying-segment"
        self.assertFalse(MODULE.validate(plan)["ok"])

    def test_approved_plan_requires_all_units_approved(self):
        plan = valid_plan()
        plan["subtitle_units"][0]["review_status"] = "pending"
        self.assertFalse(MODULE.validate(plan)["ok"])

    def test_validation_does_not_mutate_input(self):
        plan = valid_plan()
        before = copy.deepcopy(plan)
        MODULE.validate(plan)
        self.assertEqual(plan, before)

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

    def test_words_health_role_must_be_valid(self):
        plan = valid_plan()
        plan["policy"]["words_health"]["role"] = "authoritative"
        self.assertFalse(MODULE.validate(plan)["ok"])

    def test_words_health_role_fallback_allowed(self):
        plan = valid_plan()
        # fallback is valid only when word timing is not "valid"
        plan["policy"]["words_health"] = {"status": "unavailable", "role": "fallback"}
        self.assertTrue(MODULE.validate(plan)["ok"], MODULE.validate(plan))

    def test_final_draft_audit_requires_final_subtitle_authority(self):
        plan = valid_plan()
        plan["mode"] = "final_draft_audit"
        plan["source"]["text_authority"] = "asr"
        plan["source"]["subtitle_reference"] = {"id": "subtitle-ref", "hash": "sha256:subtitle"}
        self.assertFalse(MODULE.validate(plan)["ok"])

    def test_changed_order_requires_verified_mapping_for_approved_plan(self):
        plan = valid_plan()
        plan["comparison"] = {
            "source_order_hash": "sha256:source",
            "target_order_hash": "sha256:target",
            "source_sequence": ["U1", "U2"],
            "target_sequence": ["U2", "U1"],
            "remap_status": "verified",
            "semantic_mapping": [
                {"source": "U1", "target": "U1"},
                {"source": "U2", "target": "U2"},
            ],
        }
        self.assertTrue(MODULE.validate(plan)["ok"], MODULE.validate(plan))
        plan["comparison"]["remap_status"] = "pending"
        self.assertFalse(MODULE.validate(plan)["ok"])


if __name__ == "__main__":
    unittest.main()
