import copy
import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "validate_analysis_report.py"
SPEC = importlib.util.spec_from_file_location("validate_analysis_report", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load {SCRIPT}")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def valid_report():
    return {
        "report_type": "final_draft_audit",
        "source": {
            "text_authority": "final_visible_subtitle",
            "subtitle_reference": {"id": "subtitle-ref", "hash": "sha256:subtitle", "status": "approved"},
            "evidence": ["rendered_subtitle", "edited_audio"],
        },
        "evidence": [{"kind": "rendered_subtitle", "status": "available"}],
        "timeline_comparison": {
            "source_order_hash": "sha256:source",
            "target_order_hash": "sha256:target",
            "source_sequence": ["U1"],
            "target_sequence": ["U1"],
            "remap_status": "not_required",
            "semantic_mapping": [],
        },
        "semantic_groups": [{
            "id": "G1",
            "semantic_unit_id": "U1",
            "final_subtitle_text": "Generic final subtitle",
            "role": "answer",
            "context_dependencies": ["previous question"],
            "speaker_id": "speaker-a",
            "speaker_function": "respondent",
            "short_video_reason": "Carries the answer",
            "protected_fact_flags": {"number": False, "model": False, "condition": False},
            "needs_listen": False,
            "review_status": "approved",
        }],
        "protected_facts": [],
        "discrepancies": [],
        "review": {"status": "approved", "flags": []},
    }


class AnalysisReportTests(unittest.TestCase):
    def test_valid_report(self):
        result = MODULE.validate(valid_report())
        self.assertTrue(result["ok"], result)

    def test_asr_mismatch_requires_human_review(self):
        report = valid_report()
        report["discrepancies"] = [{
            "type": "asr_final_mismatch",
            "summary": "ASR differs from the final subtitle",
            "review_status": "approved",
        }]
        self.assertFalse(MODULE.validate(report)["ok"])

    def test_changed_order_requires_mapping(self):
        report = valid_report()
        report["timeline_comparison"]["source_sequence"] = ["U1", "U2"]
        report["timeline_comparison"]["target_sequence"] = ["U2", "U1"]
        self.assertFalse(MODULE.validate(report)["ok"])

    def test_application_fields_are_rejected(self):
        report = valid_report()
        report["semantic_groups"][0]["track_id"] = "synthetic-track"
        self.assertFalse(MODULE.validate(report)["ok"])

    def test_validation_does_not_mutate_input(self):
        report = valid_report()
        before = copy.deepcopy(report)
        MODULE.validate(report)
        self.assertEqual(report, before)


if __name__ == "__main__":
    unittest.main()
