import copy
import sys
import unittest
from pathlib import Path

SCRIPT_ROOT = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_ROOT))
from roughcut_tools.validators import analysis_report_impl as MODULE


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

    def test_nested_destructive_fields_are_rejected(self):
        report = valid_report()
        report["evidence"].append({"kind": "review", "status": "review", "nested": {"delete": True}})
        result = MODULE.validate(report)
        self.assertFalse(result["ok"])
        self.assertTrue(any("destructive action field" in error for error in result["errors"]))

    def test_application_fields_are_rejected(self):
        report = valid_report()
        report["semantic_groups"][0]["track_id"] = "synthetic-track"
        self.assertFalse(MODULE.validate(report)["ok"])

    def test_validation_does_not_mutate_input(self):
        report = valid_report()
        before = copy.deepcopy(report)
        MODULE.validate(report)
        self.assertEqual(report, before)


    def test_missing_provenance_is_unavailable_without_mutation(self):
        data = valid_report()
        row = data["semantic_groups"][0]
        row["cli_report"] = "deterministic evidence"
        before = copy.deepcopy(data)
        result = MODULE.validate(data)
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["review_gates"]["semantic_groups[0]"]["provenance"], "unavailable")
        self.assertEqual(result["review_gates"]["semantic_groups[0]"]["human_listening"], "pending")
        self.assertEqual(data, before)

    def test_provenance_enum_and_types(self):
        for value in ("script_generated", "agent_interpreted", "unavailable"):
            data = valid_report()
            data["semantic_groups"][0]["provenance"] = value
            self.assertTrue(MODULE.validate(data)["ok"], value)
        for value in ("automatic", "human", None, [], {}):
            data = valid_report()
            data["semantic_groups"][0]["provenance"] = value
            result = MODULE.validate(data)
            self.assertFalse(result["ok"], value)
            self.assertTrue(any("provenance" in e for e in result["errors"]))

    def test_script_output_cannot_grant_human_verified(self):
        data = valid_report()
        data["semantic_groups"][0].update(provenance="human_verified", cli_report="passed", human_review=True)
        result = MODULE.validate(data)
        self.assertFalse(result["ok"])
        self.assertTrue(any("human_verdict" in e for e in result["errors"]))

    def test_recorded_human_verdict_can_verify(self):
        data = valid_report()
        data["semantic_groups"][0].update(provenance="human_verified", human_listening="verified",
                   human_verdict={"actor": "human", "reviewer": "human reviewer", "verdict": "approved",
                                  "scope": "human_listening", "evidence": "Recorded listening verdict"})
        result = MODULE.validate(data)
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["review_gates"]["semantic_groups[0]"]["human_listening"], "verified")

    def test_agent_analysis_cannot_clear_human_listening(self):
        data = valid_report()
        data["semantic_groups"][0].update(provenance="agent_interpreted", human_listening="verified",
                   playback="reviewed", waveform="checked")
        result = MODULE.validate(data)
        self.assertFalse(result["ok"])
        self.assertEqual(result["review_gates"]["semantic_groups[0]"]["human_listening"], "pending")

    def test_non_listening_verdict_does_not_clear_listening(self):
        data = valid_report()
        data["semantic_groups"][0].update(provenance="human_verified", human_listening="verified",
                   human_verdict={"actor": "human", "reviewer": "human reviewer", "verdict": "approved",
                                  "scope": "interpretation", "evidence": "Recorded text verdict"})
        result = MODULE.validate(data)
        self.assertFalse(result["ok"])
        self.assertEqual(result["review_gates"]["semantic_groups[0]"]["human_listening"], "pending")

    def test_malformed_or_rejected_verdict_cannot_verify(self):
        for verdict in (None, {}, {"reviewer": "agent", "verdict": "approved"},
                        {"actor": "human", "reviewer": "human reviewer", "verdict": "rejected",
                         "scope": "human_listening", "evidence": "Not accepted"}):
            data = valid_report()
            data["semantic_groups"][0].update(provenance="human_verified", human_verdict=verdict)
            self.assertFalse(MODULE.validate(data)["ok"], verdict)

    def test_script_or_agent_verdict_is_not_human(self):
        for actor in ("script", "agent", None):
            data = valid_report()
            data["semantic_groups"][0].update(provenance="human_verified", human_listening="verified",
                         human_verdict={"actor": actor, "reviewer": "automated reviewer",
                                        "verdict": "approved", "scope": "human_listening",
                                        "evidence": "Playback and waveform report"})
            self.assertFalse(MODULE.validate(data)["ok"], actor)

    def test_invalid_listening_status_is_rejected(self):
        for status in ("approved", None, [], {}):
            data = valid_report()
            data["semantic_groups"][0]["human_listening"] = status
            self.assertFalse(MODULE.validate(data)["ok"], status)

    def test_evidence_provenance_is_validated(self):
        data = valid_report()
        data["evidence"][0]["provenance"] = "human_verified"
        self.assertFalse(MODULE.validate(data)["ok"])

    def test_human_review_is_boolean_flag(self):
        data = valid_report()
        data["semantic_groups"][0]["human_review"] = "approved"
        self.assertFalse(MODULE.validate(data)["ok"])


    def test_human_review_is_not_a_status(self):
        report = valid_report()
        report["semantic_groups"][0]["review_status"] = "human_review"
        self.assertFalse(MODULE.validate(report)["ok"])

    def test_wording_discrepancy_uses_pending_status_and_flag(self):
        report = valid_report()
        report["discrepancies"] = [{"type": "text_mismatch", "summary": "Wording differs",
                                    "review_status": "pending", "flags": ["human_review"]}]
        self.assertTrue(MODULE.validate(report)["ok"])

    def test_pending_listening_blocks_approved_group(self):
        report = valid_report()
        report["semantic_groups"][0].update(needs_listen=True)
        self.assertFalse(MODULE.validate(report)["ok"])
        report["semantic_groups"][0].update(review_status="pending", human_review=True)
        self.assertTrue(MODULE.validate(report)["ok"])


    def test_listening_flag_also_blocks_approved_group(self):
        report = valid_report()
        report["semantic_groups"][0]["flags"] = ["needs_listen"]
        self.assertFalse(MODULE.validate(report)["ok"])

    def test_recorded_listening_allows_listening_required_approval(self):
        report = valid_report()
        report["semantic_groups"][0].update(
            needs_listen=True, provenance="human_verified", human_listening="verified",
            human_verdict={"actor": "human", "reviewer": "human reviewer", "verdict": "approved",
                           "scope": "human_listening", "evidence": "Recorded listening approval"})
        self.assertTrue(MODULE.validate(report)["ok"])


if __name__ == "__main__":
    unittest.main()
