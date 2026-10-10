import copy
import importlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def finding(value):
    return {"status": "available", "value": value,
            "evidence": ["Supplied comparison evidence"], "verdict": "PASS"}


def valid_report():
    return {
        "report_type": "stage_comparison",
        "purpose": "stage_delta",
        "scope": ["duration", "segment_count", "containment", "overlap", "deletion",
                  "addition", "reorder", "pause_evidence", "no_asr_spans",
                  "protected_fact_exposure", "unresolved_term_exposure"],
        "stages": [{
            "stage_ref": "compared", "role": "manual fine cut", "authority": "unknown",
            "baseline": {"status": "available", "stage_ref": "accepted",
                         "designation": "user_designated"},
            "duration": finding(1.5), "segment_count": finding(1),
            "relationships": {name: finding("No observed change") for name in
                              ("containment", "overlap", "deletion", "addition", "reorder")},
            "pause_evidence": finding([{"functional_class": "breath", "observation": "Preserved"}]),
            "no_asr_spans": finding([]), "protected_fact_exposure": finding([]),
            "unresolved_term_exposure": finding([]),
        }, {
            "stage_ref": "accepted", "role": "rough cut", "authority": "no",
            "baseline": {"status": "unavailable"},
            "duration": finding(1.5), "segment_count": finding(1),
            "relationships": {name: {"status": "unavailable", "verdict": "UNVERIFIED"}
                              for name in ("containment", "overlap", "deletion", "addition", "reorder")},
            "pause_evidence": finding([]), "no_asr_spans": finding([]),
            "protected_fact_exposure": finding([]), "unresolved_term_exposure": finding([]),
        }],
    }


class StageComparisonReportTests(unittest.TestCase):
    def validate(self, report):
        name = "roughcut_tools.validators.stage_comparison_report"
        self.assertIsNotNone(importlib.util.find_spec(name), "comparison validator is missing")
        return importlib.import_module(name).validate_stage_comparison_report(report)

    def test_valid_report_and_envelope_without_mutation(self):
        report = valid_report()
        before = copy.deepcopy(report)
        result = self.validate(report)
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["report_type"], "stage_comparison_report_validation")
        self.assertEqual(result["summary"]["stage_count"], 2)
        self.assertEqual(report, before)

    def test_missing_required_fields_are_not_invented(self):
        for field in ("role", "authority", "baseline", "duration", "segment_count",
                      "relationships", "pause_evidence", "no_asr_spans",
                      "protected_fact_exposure", "unresolved_term_exposure"):
            with self.subTest(field=field):
                report = valid_report()
                del report["stages"][0][field]
                result = self.validate(report)
                self.assertFalse(result["ok"])
                self.assertTrue(any(field in error for error in result["errors"]))

    def test_missing_relationship_and_verdict_rejected(self):
        for field in ("containment", "overlap", "deletion", "addition", "reorder"):
            report = valid_report()
            del report["stages"][0]["relationships"][field]
            self.assertFalse(self.validate(report)["ok"])
        report = valid_report()
        del report["stages"][0]["duration"]["verdict"]
        self.assertFalse(self.validate(report)["ok"])

    def test_unavailable_baseline_requires_unavailable_relationships(self):
        report = valid_report()
        report["stages"][0]["baseline"] = {"status": "unavailable"}
        self.assertFalse(self.validate(report)["ok"])
        report["stages"][0]["relationships"] = copy.deepcopy(report["stages"][1]["relationships"])
        self.assertTrue(self.validate(report)["ok"])

    def test_baseline_must_be_explicit_known_and_appropriate(self):
        for baseline in ({"status": "available", "stage_ref": "accepted"},
                         {"status": "available", "stage_ref": "absent", "designation": "user_designated"},
                         {"status": "not_assessed"},
                         {"status": "available", "stage_ref": "accepted", "designation": "inferred"}):
            report = valid_report()
            report["stages"][0]["baseline"] = baseline
            self.assertFalse(self.validate(report)["ok"])
        for purpose in ("content_completeness", "preservation"):
            report = valid_report()
            report["purpose"] = purpose
            self.assertFalse(self.validate(report)["ok"])

    def test_status_scope_and_evidence_consistency(self):
        for value in (None, 0, {"status": "available", "value": 0, "evidence": [], "verdict": "PASS"},
                      {"status": "not_assessed", "verdict": "UNVERIFIED"},
                      {"status": "unavailable", "value": 0, "verdict": "PASS"}):
            report = valid_report()
            report["stages"][0]["duration"] = value
            self.assertFalse(self.validate(report)["ok"])
        report = valid_report()
        report["stages"][0]["duration"] = {"status": "unavailable", "verdict": "UNVERIFIED"}
        self.assertTrue(self.validate(report)["ok"])
        report["scope"].remove("duration")
        for stage in report["stages"]:
            stage["duration"] = {"status": "not_assessed", "verdict": "UNVERIFIED"}
        self.assertTrue(self.validate(report)["ok"])

    def test_source_and_manual_authority_baselines_are_valid(self):
        report = valid_report()
        report["purpose"] = "content_completeness"
        report["stages"][1]["role"] = "source"
        report["stages"][0]["baseline"]["designation"] = "source_role"
        self.assertTrue(self.validate(report)["ok"])
        report["purpose"] = "preservation"
        report["stages"][1]["role"] = "manual fine cut"
        report["stages"][1]["authority"] = "yes"
        report["stages"][0]["baseline"]["designation"] = "user_designated"
        self.assertTrue(self.validate(report)["ok"])

    def test_out_of_scope_cannot_claim_available_and_unverified_can_have_evidence(self):
        report = valid_report()
        report["scope"].remove("duration")
        self.assertFalse(self.validate(report)["ok"])
        report = valid_report()
        report["stages"][0]["duration"]["verdict"] = "UNVERIFIED"
        self.assertTrue(self.validate(report)["ok"])

    def test_cli_missing_input_returns_input_error(self):
        completed = subprocess.run(
            [sys.executable, "-X", "utf8", str(ROOT / "scripts" / "roughcut_tool.py"),
             "validate", "comparison-report", str(ROOT / "temp" / "missing-report.json")],
            capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(completed.returncode, 2)
        self.assertTrue(json.loads(completed.stdout)["input_errors"])

    def test_malformed_counts_and_inventory_rejected(self):
        for field, values in (("duration", (-1, True, "unknown", float("nan"), float("inf"))),
                              ("segment_count", (-1, True, 1.5)),
                              ("pause_evidence", ([{"duration": 1}], "silence")),
                              ("no_asr_spans", ("silence",)),
                              ("protected_fact_exposure", (False,))):
            for value in values:
                report = valid_report()
                report["stages"][0][field] = finding(value)
                self.assertFalse(self.validate(report)["ok"], (field, value))

    def test_forbidden_edit_fields_at_any_depth(self):
        for key in ("fine_cut_direction", "cleanup_candidates", "proposed_changes", "draft_path",
                    "track_id", "segment_id", "target_locator", "source_locator", "write_back",
                    "execution_handoff", "apply", "instructions", "action"):
            report = valid_report()
            report["stages"][0]["no_asr_spans"]["value"] = [{"nested": {key: "delete"}}]
            result = self.validate(report)
            self.assertFalse(result["ok"])
            self.assertTrue(any(key in error for error in result["errors"]))

    def test_undeclared_structural_fields_rejected(self):
        for location in ("report", "stage", "baseline", "relationships", "finding",
                         "unavailable_baseline", "unavailable_finding", "not_assessed_finding"):
            with self.subTest(location=location):
                report = valid_report()
                stage = report["stages"][0]
                if location == "not_assessed_finding":
                    report["scope"].remove("duration")
                    for item in report["stages"]:
                        item["duration"] = {"status": "not_assessed", "verdict": "UNVERIFIED"}
                containers = {
                    "report": report, "stage": stage, "baseline": stage["baseline"],
                    "relationships": stage["relationships"], "finding": stage["duration"],
                    "unavailable_baseline": report["stages"][1]["baseline"],
                    "unavailable_finding": report["stages"][1]["relationships"]["overlap"],
                    "not_assessed_finding": stage["duration"],
                }
                containers[location]["undeclared_field"] = "Unexpected structural data"
                result = self.validate(report)
                self.assertFalse(result["ok"])
                self.assertTrue(any("undeclared_field" in error for error in result["errors"]))

    def test_project_locators_rejected_at_root_and_in_extensible_metadata(self):
        for key in ("timeline_id", "project_id", "draft_id", "track_path", "segment_path",
                    "jianying_locator", "project_locator", "locator", "locators"):
            for location in ("report", "metadata"):
                with self.subTest(key=key, location=location):
                    report = valid_report()
                    container = report
                    if location == "metadata":
                        container = {key: "Application reference"}
                        report["stages"][0]["no_asr_spans"]["value"] = [{
                            "observation": "Unrecognized speech needs review",
                            "metadata": {"nested": [container]},
                        }]
                    else:
                        container[key] = "Application reference"
                    result = self.validate(report)
                    self.assertFalse(result["ok"])
                    self.assertTrue(any(key in error for error in result["errors"]))

    def test_read_only_observation_metadata_remains_extensible(self):
        report = valid_report()
        report["stages"][0]["no_asr_spans"]["value"] = [{
            "observation": "Unrecognized speech needs review",
            "metadata": {"review_notes": [{"confidence": "uncertain"}]},
        }]
        before = copy.deepcopy(report)
        self.assertTrue(self.validate(report)["ok"])
        self.assertEqual(report, before)

    def test_malformed_reports_return_validation_errors(self):
        for report in (None, [], {}, {"report_type": []},
                       dict(valid_report(), stages=[]), dict(valid_report(), scope=[{}])):
            self.assertFalse(self.validate(report)["ok"])
        for field, value in (("role", []), ("authority", {}), ("stage_ref", "")):
            report = valid_report()
            report["stages"][0][field] = value
            self.assertFalse(self.validate(report)["ok"])
        report = valid_report()
        report["stages"][1]["stage_ref"] = "compared"
        self.assertFalse(self.validate(report)["ok"])

    def test_cli_validation_is_read_only_and_returns_contract(self):
        temp_root = ROOT / "temp"
        temp_root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=temp_root) as directory:
            path = Path(directory) / "report.json"
            path.write_text(json.dumps(valid_report()), encoding="utf-8")
            before = path.read_bytes()
            command = [sys.executable, "-X", "utf8", str(ROOT / "scripts" / "roughcut_tool.py"),
                       "validate", "comparison-report", str(path)]
            completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            self.assertEqual(json.loads(completed.stdout)["report_type"], "stage_comparison_report_validation")
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(list(Path(directory).iterdir()), [path])
            path.write_text("{}", encoding="utf-8")
            completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(completed.returncode, 1)


if __name__ == "__main__":
    unittest.main()
