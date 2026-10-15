from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT_ROOT = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

import roughcut_tool
import roughcut_tools.workflow as workflow


class WorkflowScopeTests(unittest.TestCase):
    def test_workflow_requires_scope(self):
        report = workflow.run_fixed_workflow({})

        self.assertFalse(report["ok"])
        self.assertTrue(any(error.startswith("scope_required") for error in report["input_errors"]))

    def test_workflow_rejects_invalid_scope(self):
        report = workflow.run_fixed_workflow({"scope": "everything"})

        self.assertFalse(report["ok"])
        self.assertTrue(any(error.startswith("invalid_scope") for error in report["input_errors"]))

    def test_content_scope_only_runs_content_stages(self):
        ok = {"ok": True, "data": {}, "errors": [], "input_errors": [], "warnings": []}
        transcript = {"segments": []}
        with (
            patch.object(workflow, "audit_material_completeness", return_value=ok) as audit,
            patch.object(workflow, "apply_dictionary_corrections", return_value={**ok, "data": {"transcript": transcript, "corrections": []}}) as correct,
            patch.object(workflow, "build_playback_map", return_value={**ok, "data": {
                "mapping_status": "verified", "units": [{"id": "u1", "start_us": 0, "end_us": 1}],
            }}) as playback,
            patch.object(workflow, "extract_waveform_evidence", return_value=ok) as waveform,
            patch.object(workflow, "scan_all", return_value=ok) as scans,
            patch.object(workflow, "build_waveform_alignment_plan", return_value=ok) as alignment,
        ):
            report = workflow.run_fixed_workflow({
                "scope": "content",
                "inputs": {"video": "clip.mp4"},
                "transcript": transcript,
                "dictionaries": [],
                "edit_map": {"segments": []},
                "subtitles": [{"text": "out of scope", "start_us": 0, "end_us": 1}],
                "audio": "ignored.wav",
            })

        self.assertTrue(report["ok"], report)
        self.assertEqual(report["data"].get("scope"), "content")
        self.assertEqual(report["data"]["executed_stages"], ["material_audit", "transcript_correction", "playback_map"])
        self.assertEqual(report["data"]["skipped_stages"]["waveform_evidence"], "not_requested")
        self.assertEqual(report["data"]["blocked_work"], [])
        audit.assert_called_once()
        correct.assert_called_once()
        playback.assert_called_once()
        waveform.assert_not_called()
        scans.assert_not_called()
        alignment.assert_not_called()

    def test_delivery_scope_runs_candidates_without_subtitle_or_content_stages(self):
        ok_scan = {"ok": True, "data": {"pause_scan_status": "executed", "scans": [], "candidates": []}}
        ok = {"ok": True, "data": {}, "errors": [], "input_errors": [], "warnings": []}
        transcript = {"segments": []}
        with (
            patch.object(workflow, "audit_material_completeness", return_value=ok) as audit,
            patch.object(workflow, "apply_dictionary_corrections", return_value={**ok, "data": {"transcript": transcript, "corrections": []}}) as correct,
            patch.object(workflow, "build_playback_map", return_value={**ok, "data": {"mapping_status": "verified", "units": []}}) as playback,
            patch.object(workflow, "extract_waveform_evidence", wraps=workflow.extract_waveform_evidence) as waveform,
            patch.object(workflow, "scan_all", return_value=ok_scan) as scans,
            patch.object(workflow, "build_waveform_alignment_plan", return_value=ok) as alignment,
            patch.object(workflow, "build_generated_subtitle_units", return_value={**ok, "data": {"subtitle_units": []}}) as generate,
        ):
            report = workflow.run_fixed_workflow({
                "scope": "delivery",
                "subtitle_mode": "generate",
                "inputs": {"video": "ignored.mp4"},
                "transcript": {"segments": []},
                "dictionaries": [],
                "edit_map": {"segments": []},
                "playback_map": {"mapping_status": "verified", "units": [{"id": "u1", "text": "重复", "start_us": 0, "end_us": 1}]},
                "subtitles": [],
                "audio": {"duration_us": 1000, "pauses": []},
            })

        self.assertTrue(report["ok"], report)
        self.assertEqual(report["data"].get("scope"), "delivery")
        self.assertIsNone(report["data"]["subtitle_mode"])
        self.assertEqual(report["data"]["executed_stages"], ["waveform_evidence", "candidate_scans"])
        self.assertEqual(report["data"]["skipped_stages"]["subtitle_alignment"], "not_requested")
        self.assertFalse(set(report["data"]["blocked_work"]) & {"material_audit", "transcript_correction", "playback_map", "subtitle_generation", "subtitle_alignment"})
        audit.assert_not_called()
        correct.assert_not_called()
        playback.assert_not_called()
        waveform.assert_called_once()
        scans.assert_called_once()
        alignment.assert_not_called()
        generate.assert_not_called()

    def test_all_scope_keeps_delivery_scans_when_subtitle_generation_is_blocked(self):
        ok_waveform = {
            "ok": True,
            "data": {"duration_us": 1_000, "pauses": []},
            "errors": [],
            "input_errors": [],
            "warnings": [],
        }
        ok_scan = {"ok": True, "data": {"pause_scan_status": "executed"}, "errors": [], "input_errors": [], "warnings": []}
        with (
            patch.object(workflow, "extract_waveform_evidence", return_value=ok_waveform) as waveform,
            patch.object(workflow, "scan_all", return_value=ok_scan) as scans,
            patch.object(workflow, "build_generated_subtitle_units") as generate,
        ):
            report = workflow.run_fixed_workflow({
                "scope": "all",
                "subtitle_mode": "generate",
                "subtitles": [],
                "audio": {"duration_us": 1_000, "pauses": []},
                "playback_map": {
                    "mapping_status": "verified",
                    "units": [{"id": "u1", "text": "候选扫描", "start_us": 0, "end_us": 1_000}],
                },
            })

        self.assertEqual(report["data"].get("scope"), "all")
        self.assertEqual(report["data"]["executed_stages"], ["waveform_evidence", "candidate_scans"])
        self.assertEqual(report["data"]["blocked_work"], ["subtitle_alignment", "subtitle_generation"])
        waveform.assert_called_once()
        scans.assert_called_once()
        generate.assert_not_called()

    def test_delivery_scope_marks_invalid_verified_playback_map_unavailable(self):
        ok_waveform = {
            "ok": True,
            "data": {"duration_us": 1_000, "pauses": []},
            "errors": [],
            "input_errors": [],
            "warnings": [],
        }
        invalid_maps = [
            {"mapping_status": "verified", "units": []},
            {"mapping_status": "verified", "units": [{"id": "u1", "text": "异常", "start_us": -1, "end_us": 10}]},
        ]
        for playback_map in invalid_maps:
            with self.subTest(playback_map=playback_map):
                with (
                    patch.object(workflow, "extract_waveform_evidence", return_value=ok_waveform) as waveform,
                    patch.object(
                        workflow,
                        "scan_all",
                        return_value={"ok": True, "data": {"pause_scan_status": "executed"}, "errors": [], "input_errors": [], "warnings": []},
                    ) as scans,
                ):
                    report = workflow.run_fixed_workflow({
                        "scope": "delivery",
                        "audio": {"duration_us": 1_000, "pauses": []},
                        "playback_map": playback_map,
                    })

                self.assertEqual(report["data"]["evidence_status"]["playback_map"], "unavailable")
                self.assertEqual(report["data"]["blocked_work"], ["candidate_scans"])
                self.assertNotIn("candidate_scans", report["data"]["stages"])
                waveform.assert_called_once()
                scans.assert_not_called()

    def test_all_scope_does_not_block_supplied_playback_map_when_edit_map_is_present(self):
        report = workflow.run_fixed_workflow({
            "scope": "all",
            "subtitle_mode": "existing",
            "subtitles": [{"id": "cue", "text": "已对齐", "start_us": 0, "end_us": 500}],
            "audio": {"duration_us": 1_000, "pauses": []},
            "transcript": {"segments": []},
            "edit_map": {"segments": []},
            "playback_map": {
                "mapping_status": "verified",
                "units": [{"id": "u1", "text": "已映射", "start_us": 0, "end_us": 500}],
            },
        })

        self.assertTrue(report["ok"], report)
        self.assertEqual(report["data"]["evidence_status"]["playback_map"], "available")
        self.assertNotIn("playback_map", report["data"]["blocked_work"])
        self.assertEqual(report["data"]["skipped_stages"]["playback_map"], "not_applicable")

    def test_subtitle_alignment_scope_omits_content_and_candidate_stages(self):
        ok = {"ok": True, "data": {}, "errors": [], "input_errors": [], "warnings": []}
        transcript = {"segments": []}
        with (
            patch.object(workflow, "audit_material_completeness", return_value=ok) as audit,
            patch.object(workflow, "apply_dictionary_corrections", return_value={**ok, "data": {"transcript": transcript, "corrections": []}}) as correct,
            patch.object(workflow, "build_playback_map", return_value={**ok, "data": {"mapping_status": "verified", "units": []}}) as playback,
            patch.object(workflow, "extract_waveform_evidence", wraps=workflow.extract_waveform_evidence) as waveform,
            patch.object(workflow, "scan_all", return_value={"ok": True, "data": {}}) as scans,
        ):
            report = workflow.run_fixed_workflow({
                "scope": "subtitle_alignment",
                "subtitle_mode": "existing",
                "inputs": {"video": "ignored.mp4"},
                "transcript": {"segments": []},
                "dictionaries": [],
                "edit_map": {"segments": []},
                "subtitles": [{"id": "cue", "text": "保存字幕", "start_us": 0, "end_us": 500_000}],
                "audio": {"duration_us": 1_000_000, "pauses": []},
            })

        self.assertTrue(report["ok"], report)
        self.assertEqual(report["data"].get("scope"), "subtitle_alignment")
        self.assertEqual(report["data"]["executed_stages"], ["waveform_evidence", "subtitle_alignment"])
        self.assertEqual(report["data"]["skipped_stages"]["candidate_scans"], "not_requested")
        self.assertFalse(set(report["data"]["blocked_work"]) & {"material_audit", "transcript_correction", "playback_map", "candidate_scans"})
        self.assertNotIn("material_audit", report["data"]["stages"])
        self.assertNotIn("playback_map", report["data"]["stages"])
        self.assertNotIn("candidate_scans", report["data"]["stages"])
        audit.assert_not_called()
        correct.assert_not_called()
        playback.assert_not_called()
        waveform.assert_called_once()
        scans.assert_not_called()

    def test_subtitle_alignment_loads_transcript_for_empty_subtitle_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subtitles_path = root / "subtitles.json"
            transcript_path = root / "transcript.json"
            subtitles_path.write_text("[]", encoding="utf-8")
            transcript_path.write_text(json.dumps({"segments": [{
                "id": "s1", "text": "生成字幕", "start_us": 0, "end_us": 500_000,
            }]}), encoding="utf-8")
            report = workflow.run_fixed_workflow({
                "scope": "subtitle_alignment",
                "subtitle_mode": "auto",
                "subtitles": str(subtitles_path),
                "transcript": str(transcript_path),
                "audio": {"duration_us": 1_000_000, "pauses": []},
            })

        self.assertTrue(report["ok"], report)
        self.assertIn("subtitle_generation", report["data"]["stages"])
        self.assertIn("subtitle_alignment", report["data"]["stages"])

    def test_cli_scope_overrides_bundle(self):
        with tempfile.TemporaryDirectory() as directory:
            bundle_path = Path(directory) / "workflow.json"
            bundle_path.write_text(json.dumps({
                "scope": "content",
                "subtitles": [{"id": "cue", "text": "保存字幕", "start_us": 0, "end_us": 100}],
                "audio": {"duration_us": 1000, "pauses": []},
            }), encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = roughcut_tool.main(["workflow", "--input", str(bundle_path), "--scope", "subtitle_alignment"])

        self.assertEqual(code, 0, output.getvalue())
        self.assertEqual(json.loads(output.getvalue())["data"]["scope"], "subtitle_alignment")

    def test_validate_alignment_does_not_read_audio(self):
        with tempfile.TemporaryDirectory() as directory:
            plan_path = Path(directory) / "plan.json"
            report = workflow.build_waveform_alignment_plan(
                {"duration_us": 1000, "pauses": []},
                [{"id": "cue", "text": "字幕", "start_us": 0, "end_us": 500}],
            )
            plan_path.write_text(json.dumps(report), encoding="utf-8")
            output = io.StringIO()
            with patch.object(roughcut_tool, "extract_waveform_evidence") as read_audio:
                with contextlib.redirect_stdout(output):
                    code = roughcut_tool.main(["validate", "alignment", str(plan_path)])

        self.assertEqual(code, 0, output.getvalue())
        read_audio.assert_not_called()
        self.assertTrue(json.loads(output.getvalue())["ok"])


if __name__ == "__main__":
    unittest.main()
