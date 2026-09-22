import tempfile
import unittest
from pathlib import Path
import sys

SCRIPT_ROOT = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from roughcut_tools.generic_content import check_generic_content
from roughcut_tools.learning import build_learning_report
from roughcut_tools.timeline_compare import build_stage_diff


class LearningAndStageDiffTests(unittest.TestCase):
    def test_stage_diff_requires_mapping_when_order_changes(self):
        report = build_stage_diff(
            {"units": [{"id": "a", "start_us": 0, "end_us": 10}, {"id": "b", "start_us": 10, "end_us": 20}]},
            {"units": [{"id": "b", "start_us": 0, "end_us": 10}, {"id": "a", "start_us": 10, "end_us": 20}]},
        )
        self.assertFalse(report["ok"])
        self.assertEqual(report["data"]["remap_status"], "pending")

    def test_stage_diff_separates_display_only_from_semantic_text_changes(self):
        source = {"units": [{"id": "u1", "text": "完整句子", "start_us": 0, "end_us": 100}]}
        target = {"units": [{"id": "u1", "text": "短显示", "text_authority": "packaging_display_text", "packaged": True, "start_us": 0, "end_us": 80}]}
        report = build_stage_diff(source, target)
        change = report["data"]["changes"][0]
        self.assertEqual(change["text_change"], "display_only")
        self.assertIn("shortened", change["kinds"])
        target["units"][0]["text_authority"] = "final_visible_subtitle"
        report = build_stage_diff(source, target)
        self.assertEqual(report["data"]["changes"][0]["text_change"], "semantic_or_subtitle_change")

    def test_compound_exclusion_is_annotation_only(self):
        report = build_stage_diff(
            {"units": [{"id": "u1", "start_us": 0, "end_us": 100}]},
            {"units": [{"id": "u1", "start_us": 0, "end_us": 100}]},
            exclusions=[{"start_us": 0, "end_us": 100, "reason": "compound"}],
        )
        self.assertEqual(report["data"]["excluded_unit_ids"], ["u1"])
        self.assertEqual(report["data"]["changes"][0]["excluded"], True)

    def test_learning_report_rejects_application_fields(self):
        report = build_learning_report([
            {
                "id": "l1",
                "area": "subtitle_alignment",
                "pattern": "waveform remains the boundary authority",
                "evidence_level": "plan_consistency",
                "generalizability": "generic",
                "promotion_status": "approved_generic",
                "draft_path": "must-not-appear",
            }
        ], source_kind="synthetic_fixture")
        self.assertFalse(report["ok"])
        self.assertTrue(any("draft_path" in error for error in report["errors"]))

    def test_learning_report_rejects_unknown_fields_and_requires_project_case_ref(self):
        unknown = build_learning_report([{
            "id": "l1",
            "area": "motion",
            "pattern": "generic",
            "evidence_level": "plan_consistency",
            "generalizability": "generic",
            "promotion_status": "pending",
            "copy": "project-specific text",
        }], source_kind="synthetic_fixture")
        self.assertFalse(unknown["ok"])
        self.assertTrue(any("copy" in error for error in unknown["errors"]))

        missing_ref = build_learning_report([], source_kind="project_case")
        self.assertFalse(missing_ref["ok"])
        self.assertTrue(any("source.case_ref" in error for error in missing_ref["errors"]))

    def test_generic_guard_accepts_skill_text_and_runtime_forbidden_marker(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "generic.md"
            path.write_text("semantic unit and relative layout", encoding="utf-8")
            self.assertTrue(check_generic_content([path])["ok"])
            blocked = check_generic_content([path], forbidden_literals=["semantic unit"])
            self.assertFalse(blocked["ok"])


if __name__ == "__main__":
    unittest.main()
