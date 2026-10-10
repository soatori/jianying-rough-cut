from __future__ import annotations

import contextlib
import hashlib
import io
import json
import shutil
import sys
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

SCRIPT_ROOT = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

import roughcut_tools.waveform as waveform_module
from roughcut_tool import main as roughcut_main
from roughcut_tools.candidate_scans import detect_pause_candidates, scan_all
from roughcut_tools.material_audit import audit_material_completeness
from roughcut_tools.playback_map import build_playback_map
from roughcut_tools.retrospective import build_retrospective_diff
from roughcut_tools.subtitle_alignment import build_subtitle_alignment_plan
from roughcut_tools.subtitle_generation import (
    build_generated_subtitle_units,
    render_srt,
)
from roughcut_tools.timeline_compare import compare_timeline_orders
from roughcut_tools.transcript_correction import apply_dictionary_corrections
from roughcut_tools.validators.alignment_plan import validate_alignment_plan
from roughcut_tools.waveform import (
    build_waveform_alignment_plan,
    extract_waveform_evidence,
)
from roughcut_tools.workflow import run_fixed_workflow


class RoughcutToolTests(unittest.TestCase):
    def test_pause_threshold_only_generates_unclassified_review_candidates(self):
        report = detect_pause_candidates({"pauses": [
            {"start_us": 0, "end_us": 99},
            {"start_us": 200, "end_us": 300, "pause_function": "breath"},
            {"start_us": 400, "end_us": 10000},
        ]}, {"pause_min_us": 100})
        self.assertTrue(report["ok"], report)
        self.assertEqual(report["data"].get("pause_function_options"), [
            "hesitation", "sentence_boundary", "speaker_handoff", "topic_shift",
            "emphasis", "emotional_beat", "breath", "failed_take_gap", "edit_damage",
        ])
        rows = report["data"]["candidates"]
        self.assertEqual(len(rows), 2)
        self.assertEqual([r.get("duration_us") for r in rows], [100, 9600])
        for row in rows:
            self.assertEqual(row["action"], "review")
            self.assertEqual(row.get("pause_function"), "unavailable")
            self.assertIs(row.get("contextual_review_required"), True)
            self.assertIs(row.get("candidate_only"), True)
            self.assertEqual(row.get("provenance"), "script_generated")
            self.assertEqual(row.get("human_listening"), "pending")

    def test_pause_config_cannot_inject_automatic_actions(self):
        for config in ({"action": "delete"}, {"automatic_action": "join"},
                       {"metadata": {"auto_delete": True}}):
            report = detect_pause_candidates({"pauses": [{"start_us": 0, "end_us": 200000}]}, config)
            self.assertFalse(report["ok"], report)
            self.assertNotIn("delete", json.dumps(report.get("data")))
            self.assertNotIn("join", json.dumps(report.get("data")))

    def test_pause_settings_validated_before_reading_media(self):
        for config in ({"pause_min_us": "invalid"}, {"pause_min_us": True},
                       {"noise_db": "delete"}, {"noise_db": {"action": "join"}}):
            report = detect_pause_candidates("missing.wav", config)
            self.assertFalse(report["ok"])
            self.assertTrue(report["errors"], report)
            self.assertFalse(report["input_errors"], report)

    def test_pause_scan_accepts_shared_waveform_settings_without_echoing_them(self):
        report = detect_pause_candidates({"pauses": [{"start_us": 0, "end_us": 100}]}, {
            "pause_min_us": 100, "pause_cap_us": 200, "edge_window_us": 300,
            "tolerance_us": 20, "hop_us": 10, "window_us": 25,
            "auto_snap_within_tolerance": False,
        })
        self.assertTrue(report["ok"], report)
        self.assertEqual(report["data"]["config"], {"pause_min_us": 100})
        self.assertEqual(report["data"]["candidates"][0]["action"], "review")

    def test_material_audit_blocks_missing_evidence(self):
        report = audit_material_completeness({"video": "missing" + "." + "mp4"})
        self.assertFalse(report["ok"])
        self.assertEqual(report["data"]["status"], "partial")

    def test_dictionary_correction_preserves_timing_shape(self):
        transcript = {"segments": [{"id": "s1", "text": "Clock 参数", "start_us": 1, "end_us": 2}]}
        report = apply_dictionary_corrections(transcript, [{"Clock": "Grok"}])
        self.assertTrue(report["ok"])
        self.assertEqual(report["data"]["transcript"]["segments"][0]["text"], "Grok 参数")
        self.assertEqual(report["data"]["transcript"]["segments"][0]["start_us"], 1)

    def test_generated_subtitles_require_timing_and_preserve_corrections(self):
        transcript = {
            "segments": [{
                "id": "u1",
                "text": "正确术语",
                "start_us": 100_000,
                "end_us": 400_000,
                "words": [{"text": "正确术语", "start_us": 100_000, "end_us": 400_000}],
            }],
            "unresolved_terms": ["待确认型号"],
        }
        report = build_generated_subtitle_units(
            transcript,
            [{"segment_id": "u1", "original": "错误术语", "corrected": "正确术语", "reason": "dictionary"}],
        )
        self.assertTrue(report["ok"], report)
        unit = report["data"]["subtitle_units"][0]
        self.assertEqual(unit["text"], "正确术语")
        self.assertEqual((unit["start_us"], unit["end_us"]), (100_000, 400_000))
        self.assertEqual(unit["corrections"][0]["segment_id"], "u1")
        self.assertEqual(report["summary"]["unresolved_term_count"], 1)

        missing_timing = build_generated_subtitle_units({"segments": [{"id": "u1", "text": "纯文本"}]})
        self.assertFalse(missing_timing["ok"])
        self.assertTrue(any("start_us" in error for error in missing_timing["errors"]))

    def test_generated_subtitles_accept_timed_words_and_correct_word_text(self):
        transcript = {
            "segments": [{
                "id": "u1",
                "words": [
                    {"id": "w1", "text": "错误", "start_us": 100_000, "end_us": 180_000},
                    {"id": "w2", "text": "术语", "start_us": 180_000, "end_us": 260_000},
                ],
            }],
        }
        corrected = apply_dictionary_corrections(transcript, [{"错误": "正确"}])
        self.assertTrue(corrected["ok"], corrected)
        self.assertEqual(corrected["data"]["transcript"]["segments"][0]["words"][0]["text"], "正确")
        self.assertEqual(
            corrected["data"]["transcript"]["segments"][0]["words"][0]["start_us"],
            100_000,
        )
        generated = build_generated_subtitle_units(
            corrected["data"]["transcript"],
            corrected["data"]["corrections"],
        )
        self.assertTrue(generated["ok"], generated)
        unit = generated["data"]["subtitle_units"][0]
        self.assertEqual(unit["text"], "正确术语")
        self.assertEqual((unit["start_us"], unit["end_us"]), (100_000, 260_000))

    def test_render_srt_uses_non_shortening_millisecond_conversion(self):
        srt = render_srt({"subtitle_units": [{
            "id": "u1",
            "semantic_unit_id": "u1",
            "text": "一句话",
            "start_us": 1_001,
            "end_us": 2_001,
        }]})
        self.assertIn("00:00:00,001 --> 00:00:00,003", srt)
        self.assertIn("一句话", srt)

    def test_render_srt_rejects_non_monotone_end_times(self):
        with self.assertRaisesRegex(ValueError, "non-decreasing end_us"):
            render_srt([
                {"text": "第一句", "start_us": 0, "end_us": 2_000_000},
                {"text": "第二句", "start_us": 1_000_000, "end_us": 1_500_000},
            ])

    def test_playback_map_accounts_for_speed(self):
        transcript = {"tokens": [{"id": "w1", "semantic_unit_id": "u1", "text": "词", "start_us": 100, "end_us": 300}]}
        edit_map = {"segments": [{"id": "e1", "semantic_unit_id": "u1", "source_start_us": 0, "source_end_us": 1000, "target_start_us": 500, "target_end_us": 1000, "speed": 2.0, "kept": True}]}
        report = build_playback_map(transcript, edit_map)
        self.assertTrue(report["ok"])
        self.assertEqual(report["data"]["tokens"][0]["edited_start_us"], 550)
        self.assertEqual(report["data"]["tokens"][0]["edited_end_us"], 650)

    def test_candidate_scans_never_emit_delete(self):
        report = scan_all({"units": [{"id": "a", "text": "重复内容", "start_us": 0, "end_us": 100}, {"id": "b", "text": "重复内容", "start_us": 200, "end_us": 300}]})
        self.assertEqual(report["status"], "review")
        self.assertTrue(report["data"]["candidates"])
        self.assertTrue(all(item["action"] == "review" for item in report["data"]["candidates"]))

    def test_alignment_plan_marks_boundaries_for_human_review(self):
        playback = {
            "content_plan_id": "plan-1",
            "content_plan_hash": "sha256:plan",
            "duration_us": 100,
            "mapping_status": "verified",
            "evidence": ["synthetic-token-map"],
            "target_order_hash": "sha256:x",
            "units": [{"id": "u1", "semantic_unit_id": "u1", "start_us": 10, "end_us": 20, "continuous": True}],
            "tokens": [{"id": "w1", "semantic_unit_id": "u1", "text": "字幕", "edited_start_us": 10, "edited_end_us": 20}],
        }
        report = build_subtitle_alignment_plan(playback, [{"semantic_unit_id": "u1", "text": "字幕"}])
        self.assertTrue(report["ok"])
        boundary = report["data"]["subtitle_units"][0]["boundaries"]["start"]
        self.assertEqual(boundary["review"], "pending")
        self.assertEqual(boundary["basis"], "word_boundary")

    def test_timeline_compare_blocks_duplicate_ids(self):
        report = compare_timeline_orders({"order": ["u1", "u1"]}, {"order": ["u1"]})
        self.assertFalse(report["ok"])
        self.assertEqual(report["data"]["remap_status"], "blocked")

    def test_retrospective_reports_restored_cut(self):
        proposal = {"decisions": [{"id": "d1", "action": "delete"}]}
        final = {"workflow": {"content_pass": "approved"}, "decisions": [{"id": "d1", "action": "keep"}]}
        report = build_retrospective_diff(proposal, final)
        self.assertTrue(report["ok"])
        self.assertEqual(report["summary"]["restored_count"], 1)

    def test_cli_blocks_incomplete_preflight(self):
        self.assertEqual(roughcut_main(["preflight", "--video", "missing" + "." + "mp4"]), 2)

    def test_playback_map_records_deleted_and_blocks_unresolved_tokens(self):
        transcript = {"segments": [{"id": "u1", "semantic_unit_id": "u1", "text": "甲乙", "tokens": [
            {"id": "a", "text": "甲", "start_us": 0, "end_us": 100},
            {"id": "b", "text": "乙", "start_us": 100, "end_us": 200},
        ]}]}
        edit_map = {"segments": [
            {"id": "cut-a", "semantic_unit_id": "u1", "source_start_us": 0, "source_end_us": 100, "kept": False},
            {"id": "keep-b", "semantic_unit_id": "u1", "source_start_us": 100, "source_end_us": 200, "target_start_us": 0, "target_end_us": 100, "speed": 1, "kept": True},
        ]}
        report = build_playback_map(transcript, edit_map)
        self.assertTrue(report["ok"])
        self.assertEqual(report["data"]["deleted_token_ids"], ["a"])
        self.assertEqual(report["data"]["tokens"][0]["id"], "b")
        unresolved = build_playback_map(transcript, {"segments": [{"id": "partial", "source_start_us": 0, "source_end_us": 100, "target_start_us": 0, "target_end_us": 100, "speed": 1, "kept": True}]})
        self.assertFalse(unresolved["ok"])
        self.assertIn("b", unresolved["data"]["unmapped_token_ids"])

    def test_playback_map_rejects_bad_speed_overlap_and_cross_boundary_tokens(self):
        transcript = {"tokens": [{"id": "w1", "semantic_unit_id": "u1", "start_us": 50, "end_us": 150}]}
        bad_speed = build_playback_map(transcript, {"segments": [{"id": "e", "source_start_us": 0, "source_end_us": 200, "target_start_us": 0, "target_end_us": 200, "speed": 0, "kept": True}]})
        self.assertFalse(bad_speed["ok"])
        overlap = build_playback_map(transcript, {"segments": [
            {"id": "a", "source_start_us": 0, "source_end_us": 120, "target_start_us": 0, "target_end_us": 120, "speed": 1, "kept": True},
            {"id": "b", "source_start_us": 100, "source_end_us": 200, "target_start_us": 120, "target_end_us": 220, "speed": 1, "kept": True},
        ]})
        self.assertFalse(overlap["ok"])
        self.assertIn("w1", overlap["data"]["unmapped_token_ids"])

    def test_map_scan_alignment_validate_chain_ignores_old_subtitle_times(self):
        transcript = {"content_plan_id": "c1", "content_plan_hash": "sha256:c1", "evidence": [{"kind": "edited_audio", "status": "available"}], "segments": [{
            "id": "u1", "semantic_unit_id": "u1", "text": "甲乙", "tokens": [
                {"id": "a", "text": "甲", "start_us": 0, "end_us": 50},
                {"id": "b", "text": "乙", "start_us": 50, "end_us": 100},
            ]
        }]}
        playback = build_playback_map(transcript, {"segments": [{"id": "e", "semantic_unit_id": "u1", "source_start_us": 0, "source_end_us": 100, "target_start_us": 200, "target_end_us": 300, "speed": 1, "kept": True}]})
        self.assertTrue(playback["ok"])
        scans = scan_all(playback["data"])
        self.assertTrue(scans["ok"])
        alignment = build_subtitle_alignment_plan(playback, [{"id": "cue", "semantic_unit_id": "u1", "text": "甲乙", "start_us": 0, "end_us": 10}])
        self.assertTrue(alignment["ok"], alignment)
        self.assertEqual(alignment["data"]["subtitle_units"][0]["start_us"], 200)
        self.assertEqual(alignment["data"]["subtitle_units"][0]["previous_range"]["start_us"], 0)
        self.assertTrue(validate_alignment_plan(alignment["data"])["ok"])
        self.assertEqual(alignment["data"]["review"]["status"], "pending")
        self.assertEqual(alignment["data"]["subtitle_units"][0]["review_status"], "pending")

    def test_pause_scan_requires_audio_and_all_scan_reports_skip(self):
        missing = detect_pause_candidates(None)
        self.assertFalse(missing["ok"])
        self.assertFalse(missing["input_errors"])
        playback = {"units": [{"id": "u1", "start_us": 0, "end_us": 100, "text": "内容"}]}
        all_report = scan_all(playback)
        self.assertTrue(all_report["ok"])
        self.assertEqual(all_report["data"]["pause_scan_status"], "not_executed")
        self.assertTrue(any("pause scan skipped" in warning for warning in all_report["warnings"]))

    def test_pause_scan_reuses_precomputed_waveform_before_path(self):
        report = detect_pause_candidates({
            "path": "missing" + "." + "wav",
            "duration_us": 1_000_000,
            "pauses": [{"start_us": 100_000, "end_us": 250_000}],
        })
        self.assertTrue(report["ok"], report)
        self.assertEqual(report["data"]["candidates"][0]["start_us"], 100_000)

    def test_waveform_alignment_uses_waveform_and_keeps_words_as_cross_check(self):
        subtitles = [{
            "id": "cue-1",
            "semantic_unit_id": "u1",
            "text": "第一句",
            "start_us": 200_000,
            "end_us": 500_000,
            "words": [{"start_us": 0, "end_us": 50_000}],
        }]
        report = build_waveform_alignment_plan({
            "duration_us": 1_000_000,
            "pauses": [
                {"start_us": 50_000, "end_us": 190_000},
                {"start_us": 500_000, "end_us": 650_000},
            ],
        }, subtitles, {"auto_snap_within_tolerance": True})
        self.assertTrue(report["ok"], report)
        plan = report["data"]
        self.assertEqual(plan["policy"]["boundary_authority"], "waveform")
        self.assertEqual(plan["policy"]["words_health"], {"status": "valid", "role": "cross_check"})
        unit = plan["subtitle_units"][0]
        self.assertEqual(unit["start_us"], 190_000)
        self.assertEqual(unit["end_us"], 500_000)
        self.assertEqual(unit["boundaries"]["start"]["basis"], "waveform")
        self.assertEqual(unit["boundaries"]["start"]["review"], "pending")
        self.assertTrue(validate_alignment_plan(plan)["ok"])

    def test_waveform_alignment_preserves_manual_ranges_by_default(self):
        subtitles = [{
            "id": "cue-1",
            "semantic_unit_id": "u1",
            "text": "人工校正",
            "start_us": 200_000,
            "end_us": 500_000,
        }]
        report = build_waveform_alignment_plan({
            "duration_us": 1_000_000,
            "pauses": [
                {"start_us": 50_000, "end_us": 190_000},
                {"start_us": 500_000, "end_us": 650_000},
            ],
        }, subtitles)
        self.assertTrue(report["ok"], report)
        unit = report["data"]["subtitle_units"][0]
        self.assertEqual((unit["start_us"], unit["end_us"]), (200_000, 500_000))
        self.assertEqual(unit["evidence"]["start"]["selection"], "waveform_candidate_only")

    def test_waveform_config_errors_are_reported_without_typeerror(self):
        report = extract_waveform_evidence(
            {"duration_us": 1_000_000, "pauses": []},
            {"pause_min_us": "not-an-integer"},
        )
        self.assertFalse(report["ok"])
        self.assertTrue(any("pause_min_us" in error for error in report["errors"]))

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "ffmpeg and ffprobe required")
    def test_audio_path_identity_includes_hash_and_stream_format(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "identity.wav"
            with wave.open(str(path), "wb") as stream:
                stream.setnchannels(1)
                stream.setsampwidth(2)
                stream.setframerate(8000)
                stream.writeframes(b"\x00\x00" * 1600)
            expected_hash = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
            report = extract_waveform_evidence(str(path))
            self.assertTrue(report["ok"], report)
            identity = report["data"].get("identity")
            self.assertIsNotNone(identity, report)
            self.assertEqual(identity.get("content_hash"), expected_hash)
            self.assertEqual(identity.get("sample_rate"), 8000)
            self.assertEqual(identity.get("channels"), 1)
            self.assertEqual(identity.get("codec"), "pcm_s16le")
            self.assertEqual(identity.get("duration_us"), 200_000)

    def test_precomputed_path_identity_is_preserved_without_probe(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "precomputed.wav"
            path.write_bytes(b"not-a-real-media-but-hashable")
            supplied_identity = {
                "content_hash": "sha256:supplied",
                "duration_us": 1_000_000,
                "sample_rate": 16_000,
                "channels": 1,
                "codec": "pcm_s16le",
            }
            report = extract_waveform_evidence({
                "path": str(path),
                "duration_us": 1_000_000,
                "pauses": [],
                "identity": supplied_identity,
            })
            self.assertTrue(report["ok"], report)
            self.assertEqual(report["data"]["identity"], supplied_identity)

    def test_alignment_plan_records_complete_audio_identity(self):
        identity = {
            "content_hash": "sha256:audio",
            "duration_us": 1_000_000,
            "sample_rate": 16_000,
            "channels": 1,
            "codec": "pcm_s16le",
        }
        subtitles = [{
            "id": "cue-1",
            "semantic_unit_id": "u1",
            "text": "身份校验",
            "start_us": 200_000,
            "end_us": 500_000,
        }]
        report = build_waveform_alignment_plan({
            "duration_us": 1_000_000,
            "pauses": [],
            "identity": identity,
        }, subtitles)
        self.assertTrue(report["ok"], report)
        evidence = next(
            item for item in report["data"]["source"]["evidence"]
            if item.get("kind") == "edited_audio"
        )
        self.assertEqual(evidence.get("identity"), identity)

    def test_waveform_alignment_does_not_promote_word_times_without_pause(self):
        subtitles = [{
            "id": "cue-1",
            "semantic_unit_id": "u1",
            "text": "连续口播",
            "start_us": 200_000,
            "end_us": 500_000,
            "words": [{"start_us": 0, "end_us": 50_000}],
        }]
        report = build_waveform_alignment_plan({"duration_us": 1_000_000, "pauses": []}, subtitles)
        self.assertTrue(report["ok"], report)
        unit = report["data"]["subtitle_units"][0]
        self.assertEqual((unit["start_us"], unit["end_us"]), (200_000, 500_000))
        self.assertEqual(unit["boundaries"]["start"]["basis"], "subtitle_boundary")
        self.assertEqual(report["data"]["policy"]["words_health"]["role"], "cross_check")

    def test_fixed_workflow_runs_waveform_once_and_reuses_it_for_scans(self):
        bundle = {
            "transcript": {
                "content_plan_id": "c1",
                "content_plan_hash": "sha256:c1",
                "evidence": [{"kind": "edited_audio", "status": "available"}],
                "segments": [{
                    "id": "u1",
                    "semantic_unit_id": "u1",
                    "text": "甲乙",
                    "tokens": [
                        {"id": "a", "text": "甲", "start_us": 0, "end_us": 100_000},
                        {"id": "b", "text": "乙", "start_us": 100_000, "end_us": 200_000},
                    ],
                }],
            },
            "edit_map": {"segments": [{
                "id": "e1",
                "semantic_unit_id": "u1",
                "source_start_us": 0,
                "source_end_us": 200_000,
                "target_start_us": 200_000,
                "target_end_us": 400_000,
                "speed": 1,
                "kept": True,
            }]},
            "audio": {
                "duration_us": 1_000_000,
                "pauses": [{"start_us": 50_000, "end_us": 190_000}],
            },
            "subtitles": [{
                "id": "cue-1",
                "semantic_unit_id": "u1",
                "text": "甲乙",
                "start_us": 200_000,
                "end_us": 400_000,
            }],
            "dictionaries": [{"甲": "甲"}],
        }
        report = run_fixed_workflow(bundle)
        self.assertTrue(report["ok"], report)
        self.assertEqual(report["summary"]["waveform_passes"], 1)
        self.assertEqual(report["summary"]["editor_writes"], 0)
        self.assertIn("waveform_evidence", report["data"]["stages"])
        self.assertIn("candidate_scans", report["data"]["stages"])
        self.assertIn("subtitle_alignment", report["data"]["stages"])
        self.assertEqual(report["data"]["subtitle_mode"], "existing")
        self.assertEqual(
            report["data"]["stages"]["subtitle_alignment"]["data"]["source"]["subtitle_origin"],
            "current_timeline",
        )
        existing_plan = report["data"]["stages"]["subtitle_alignment"]["data"]
        self.assertEqual(
            [(unit["id"], unit["text"], unit["previous_range"]) for unit in existing_plan["subtitle_units"]],
            [("cue-1", "甲乙", {"start_us": 200_000, "end_us": 400_000})],
        )
        self.assertEqual(report["data"]["stages"]["candidate_scans"]["data"]["pause_scan_status"], "executed")

    def test_workflow_summary_counts_stage_provenance_and_pending_gates(self):
        report = run_fixed_workflow({
            "subtitles": [{"id": "cue", "text": "text", "start_us": 100, "end_us": 200}],
            "audio": {"duration_us": 1000, "pauses": []},
        })
        summary = report["summary"]
        self.assertEqual(summary.get("provenance_counts"), {
            "script_generated": 2, "agent_interpreted": 0,
            "human_verified": 0, "unavailable": 0,
        })
        self.assertEqual(summary["stage_count"], 2)
        self.assertEqual(summary.get("agent_required_count"), 3)
        self.assertEqual(summary.get("gate_counts"), {
            "human_review": 3, "human_listening": 1, "pending": 4, "cleared": 0,
        })
        self.assertEqual(summary.get("blocked_stage_count"), 1)
        self.assertEqual(report["data"]["blocked_work"], ["candidate_scans"])
        self.assertTrue(all(stage["provenance"] == "script_generated"
                            for stage in report["data"]["stages"].values()))
        self.assertTrue(all(gate["status"] == "pending"
                            for gate in report["data"]["review_gates"]))

    def test_workflow_summary_exposes_missing_evidence_without_running_affected_work(self):
        subtitle = [{"id": "cue", "text": "text", "start_us": 100, "end_us": 200}]
        audio = {"duration_us": 1000, "pauses": []}
        cases = [
            ({"subtitles": subtitle}, "audio", "subtitle_alignment"),
            ({"subtitle_mode": "generate", "subtitles": [], "audio": audio},
             "transcript", "subtitle_generation"),
            ({"audio": audio}, "subtitle_state", "subtitle_alignment"),
            ({"subtitles": subtitle, "audio": audio}, "playback_map", "candidate_scans"),
            ({"subtitles": subtitle, "audio": audio,
              "playback_map": {"mapping_status": "unresolved", "unmapped_token_ids": ["token"]}},
             "playback_map", "candidate_scans"),
        ]
        for bundle, missing, blocked in cases:
            with self.subTest(missing=missing, bundle=bundle):
                report = run_fixed_workflow(bundle)
                self.assertEqual(report["data"].get("evidence_status", {}).get(missing), "unavailable")
                self.assertIn(blocked, report["data"].get("blocked_work", []))
                self.assertNotIn(blocked, report["data"]["stages"])
                self.assertGreater(report["summary"].get("unavailable_evidence_count", 0), 0)
                self.assertGreater(report["summary"].get("blocked_stage_count", 0), 0)
                self.assertEqual(report["summary"].get("gate_counts", {}).get("cleared"), 0)

    def test_workflow_summary_counts_reused_waveform_only_once(self):
        report = run_fixed_workflow({
            "subtitles": [{"id": "cue", "text": "text", "start_us": 100, "end_us": 200}],
            "audio": {"duration_us": 1000, "pauses": []},
            "playback_map": {"mapping_status": "verified", "units": [
                {"id": "unit", "text": "text", "start_us": 100, "end_us": 200},
            ]},
        })
        self.assertTrue(report["ok"], report)
        self.assertEqual(report["summary"]["waveform_passes"], 1)
        self.assertEqual(report["summary"].get("provenance_counts", {}).get("script_generated"), 3)
        self.assertEqual(report["summary"].get("blocked_stage_count"), 0)
        self.assertIn("candidate_scans", report["data"]["stages"])
        self.assertIn("subtitle_alignment", report["data"]["stages"])

    def test_workflow_summary_early_block_has_no_completed_provenance(self):
        report = run_fixed_workflow({"audio": {"duration_us": 1000, "pauses": []}})
        self.assertFalse(report["ok"])
        self.assertEqual(report["summary"]["stage_count"], 0)
        self.assertEqual(report["summary"]["waveform_passes"], 0)
        self.assertEqual(sum(report["summary"]["provenance_counts"].values()), 0)
        self.assertEqual(report["summary"]["blocked_stage_count"], 3)
        self.assertEqual(report["summary"]["unavailable_evidence_count"], 3)
        self.assertEqual(report["data"]["evidence_status"]["transcript"], "not_assessed")

    def test_workflow_summary_failed_waveform_is_not_a_successful_pass(self):
        report = run_fixed_workflow({
            "subtitles": [{"id": "cue", "text": "text", "start_us": 100, "end_us": 200}],
            "audio": {"pauses": []},
        })
        self.assertFalse(report["ok"])
        self.assertEqual(report["summary"]["stage_count"], 1)
        self.assertEqual(report["summary"]["waveform_passes"], 0)
        self.assertEqual(report["summary"]["provenance_counts"]["script_generated"], 1)
        self.assertEqual(report["summary"]["blocked_stage_count"], 3)
        self.assertEqual(report["data"]["evidence_status"]["audio"], "unavailable")
        self.assertNotIn("subtitle_alignment", report["data"]["stages"])

    def test_workflow_failed_waveform_blocks_pause_scan_but_preserves_text_scans(self):
        report = run_fixed_workflow({
            "subtitles": [{"id": "cue", "text": "text", "start_us": 100, "end_us": 200}],
            "playback_map": {"mapping_status": "verified", "units": [
                {"id": "first", "text": "repeat", "start_us": 100, "end_us": 200},
                {"id": "second", "text": "repeat", "start_us": 200, "end_us": 300},
            ]},
            "audio": {"pauses": []},
        })
        self.assertFalse(report["ok"])
        stages = report["data"]["stages"]
        self.assertFalse(stages["waveform_evidence"]["ok"])
        scans = stages["candidate_scans"]
        self.assertTrue(scans["ok"], scans)
        self.assertEqual(scans["data"]["pause_scan_status"], "not_executed")
        self.assertEqual(len(scans["data"]["scans"]), 5)
        self.assertTrue(all(scan["ok"] for scan in scans["data"]["scans"]))
        self.assertTrue(any(candidate["scan"] == "repetition"
                            for candidate in scans["data"]["candidates"]))
        self.assertEqual(report["data"]["blocked_work"], [
            "candidate_scans.pause_scan", "subtitle_alignment", "waveform_evidence",
        ])
        self.assertEqual(report["summary"]["blocked_stage_count"], 3)
        self.assertEqual(report["summary"]["waveform_passes"], 0)
        self.assertEqual(report["summary"]["gate_counts"]["cleared"], 0)
        self.assertNotIn("subtitle_alignment", stages)

    def test_workflow_summary_uses_effective_subtitle_input_for_generation_coverage(self):
        report = run_fixed_workflow({
            "subtitles": [{"id": "cue", "text": "text", "start_us": 100, "end_us": 200}],
            "inputs": {"subtitle_timing": []},
            "audio": {"duration_us": 1000, "pauses": []},
        })
        self.assertEqual(report["data"]["subtitle_mode"], "existing")
        self.assertNotIn("subtitle_generation", report["data"]["blocked_work"])
        self.assertEqual(report["data"]["evidence_status"]["transcript"], "not_assessed")

    def test_fixed_workflow_media_path_runs_one_pause_detection(self):
        with tempfile.NamedTemporaryFile(suffix=".wav") as media:
            bundle = {
                "transcript": {
                    "segments": [{
                        "id": "u1",
                        "semantic_unit_id": "u1",
                        "text": "甲乙",
                        "tokens": [
                            {"id": "a", "text": "甲", "start_us": 0, "end_us": 100_000},
                            {"id": "b", "text": "乙", "start_us": 100_000, "end_us": 200_000},
                        ],
                    }],
                },
                "edit_map": {"segments": [{
                    "id": "e1",
                    "semantic_unit_id": "u1",
                    "source_start_us": 0,
                    "source_end_us": 200_000,
                    "target_start_us": 200_000,
                    "target_end_us": 400_000,
                    "speed": 1,
                    "kept": True,
                }]},
                "audio": media.name,
                "subtitles": [{
                    "id": "cue-1",
                    "semantic_unit_id": "u1",
                    "text": "甲乙",
                    "start_us": 200_000,
                    "end_us": 400_000,
                }],
            }
            with (
                patch.object(
                    waveform_module,
                    "_probe_media",
                    return_value={"status": "available", "duration_us": 1_000_000, "metadata": {}},
                ) as probe,
                patch.object(
                    waveform_module,
                    "_detect_pauses",
                    return_value=([{"start_us": 50_000, "end_us": 190_000}], None),
                ) as detect,
            ):
                report = run_fixed_workflow(bundle)
        self.assertTrue(report["ok"], report)
        self.assertEqual(probe.call_count, 1)
        self.assertEqual(detect.call_count, 1)
        self.assertEqual(report["summary"]["waveform_passes"], 1)

    def test_fixed_workflow_generates_subtitles_from_explicit_empty_track(self):
        bundle = {
            "subtitle_mode": "auto",
            "subtitles": [],
            "transcript": {
                "segments": [{
                    "id": "u1",
                    "text": "生成字幕",
                    "start_us": 100_000,
                    "end_us": 400_000,
                    "words": [{"text": "生成字幕", "start_us": 100_000, "end_us": 400_000}],
                }],
            },
            "audio": {
                "duration_us": 1_000_000,
                "pauses": [{"start_us": 50_000, "end_us": 90_000}],
            },
        }
        report = run_fixed_workflow(bundle)
        self.assertTrue(report["ok"], report)
        self.assertEqual(report["data"]["subtitle_mode"], "generate")
        self.assertIn("subtitle_generation", report["data"]["stages"])
        self.assertIn("subtitle_alignment", report["data"]["stages"])
        plan = report["data"]["stages"]["subtitle_alignment"]["data"]
        self.assertEqual(plan["source"]["text_authority"], "generated_transcript")
        self.assertEqual(plan["source"]["subtitle_origin"], "generated_transcript")
        self.assertTrue(all(unit["review_status"] == "pending" for unit in plan["subtitle_units"]))
        self.assertEqual(report["summary"]["waveform_passes"], 1)

    def test_workflow_blocks_unknown_subtitle_state_and_generate_conflict(self):
        missing = run_fixed_workflow({"transcript": {"segments": []}})
        self.assertFalse(missing["ok"])
        self.assertTrue(any("cannot determine" in error for error in missing["input_errors"]))

        conflict = run_fixed_workflow({
            "subtitle_mode": "generate",
            "subtitles": [{"id": "cue", "text": "已有", "start_us": 0, "end_us": 100}],
            "transcript": {"segments": [{"id": "u1", "text": "新", "start_us": 0, "end_us": 100}]},
        })
        self.assertFalse(conflict["ok"])
        self.assertTrue(any("existing subtitles" in error for error in conflict["input_errors"]))

    def test_workflow_blocks_subtitle_alignment_without_audio(self):
        existing = run_fixed_workflow({
            "subtitle_mode": "existing",
            "subtitles": [{"id": "cue", "text": "已有", "start_us": 0, "end_us": 100}],
        })
        self.assertFalse(existing["ok"])
        self.assertEqual(existing["summary"]["waveform_passes"], 0)
        self.assertTrue(any("edited-timeline audio" in error for error in existing["input_errors"]))

        generated = run_fixed_workflow({
            "subtitle_mode": "generate",
            "subtitles": [],
            "transcript": {"segments": [{"id": "u1", "text": "生成", "start_us": 0, "end_us": 100}]},
        })
        self.assertFalse(generated["ok"])
        self.assertNotIn("subtitle_generation", generated["data"]["stages"])

    def test_workflow_blocks_unreadable_subtitle_state_before_generation(self):
        report = run_fixed_workflow({
            "subtitle_mode": "generate",
            "subtitles": {"report_type": "blocked", "data": None, "ok": False, "errors": ["encrypted"]},
            "transcript": {"segments": [{"id": "u1", "text": "生成", "start_us": 0, "end_us": 100}]},
            "audio": {"duration_us": 1_000_000, "pauses": []},
        })
        self.assertFalse(report["ok"])
        self.assertEqual(report["summary"]["waveform_passes"], 0)
        self.assertNotIn("subtitle_generation", report["data"]["stages"])

    def test_cli_exposes_waveform_and_fixed_workflow_commands(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evidence_path = root / "waveform.json"
            subtitles_path = root / "subtitles.json"
            bundle_path = root / "workflow.json"
            evidence = {"duration_us": 1_000_000, "pauses": [{"start_us": 50_000, "end_us": 190_000}]}
            subtitles = [{"id": "cue-1", "semantic_unit_id": "u1", "text": "一句", "start_us": 200_000, "end_us": 400_000}]
            evidence_path.write_text(json.dumps(evidence, ensure_ascii=False), encoding="utf-8")
            subtitles_path.write_text(json.dumps(subtitles, ensure_ascii=False), encoding="utf-8")
            bundle_path.write_text(json.dumps({"audio": evidence, "subtitles": subtitles}, ensure_ascii=False), encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                align_code = roughcut_main(["subtitle-align", "--audio", str(evidence_path), "--subtitles", str(subtitles_path)])
                workflow_code = roughcut_main(["workflow", "--input", str(bundle_path)])
            self.assertEqual(align_code, 0)
            self.assertEqual(workflow_code, 0)
            self.assertIn("subtitle_alignment_plan", output.getvalue())
            self.assertIn("roughcut_workflow", output.getvalue())

    def test_cli_workflow_can_override_subtitle_mode(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle_path = root / "workflow.json"
            bundle_path.write_text(
                json.dumps({
                    "subtitles": [{"id": "cue-1", "text": "已有", "start_us": 100_000, "end_us": 300_000}],
                    "audio": {"duration_us": 1_000_000, "pauses": []},
                }, ensure_ascii=False),
                encoding="utf-8",
            )
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = roughcut_main([
                    "workflow",
                    "--input", str(bundle_path),
                    "--subtitle-mode", "existing",
                ])
            self.assertEqual(code, 0, output.getvalue())
            self.assertIn('"subtitle_mode": "existing"', output.getvalue())

    def test_cli_validate_alignment_blocks_current_audio_identity_mismatch(self):
        identity = {
            "content_hash": "sha256:plan-audio",
            "duration_us": 1_000_000,
            "sample_rate": 16_000,
            "channels": 1,
            "codec": "pcm_s16le",
        }
        subtitles = [{
            "id": "cue-1",
            "semantic_unit_id": "u1",
            "text": "身份不一致",
            "start_us": 200_000,
            "end_us": 500_000,
        }]
        plan_report = build_waveform_alignment_plan({
            "duration_us": 1_000_000,
            "pauses": [],
            "identity": identity,
        }, subtitles)
        self.assertTrue(plan_report["ok"], plan_report)
        current_identity = dict(identity)
        current_identity["content_hash"] = "sha256:current-audio"
        current_identity["sample_rate"] = 48_000
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan_path = root / "plan.json"
            audio_path = root / "audio.json"
            plan_path.write_text(json.dumps(plan_report, ensure_ascii=False), encoding="utf-8")
            audio_path.write_text(json.dumps({
                "duration_us": 1_000_000,
                "pauses": [],
                "identity": current_identity,
            }, ensure_ascii=False), encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = roughcut_main([
                    "validate",
                    "alignment",
                    str(plan_path),
                    "--audio",
                    str(audio_path),
                ])
            self.assertEqual(code, 1, output.getvalue())
            report = json.loads(output.getvalue())
            self.assertTrue(any("identity mismatch" in error for error in report.get("errors", [])), report)

    def test_cli_subtitle_generate_writes_plan_and_srt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evidence_path = root / "waveform.json"
            transcript_path = root / "transcript.json"
            plan_path = root / "plan.json"
            srt_path = root / "captions.srt"
            evidence_path.write_text(
                json.dumps({"duration_us": 1_000_000, "pauses": [{"start_us": 50_000, "end_us": 90_000}]}),
                encoding="utf-8",
            )
            transcript_path.write_text(
                json.dumps({
                    "segments": [{
                        "id": "u1",
                        "text": "生成字幕",
                        "start_us": 100_000,
                        "end_us": 400_000,
                    }],
                }, ensure_ascii=False),
                encoding="utf-8",
            )
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = roughcut_main([
                    "subtitle-generate",
                    "--audio", str(evidence_path),
                    "--transcript", str(transcript_path),
                    "--out", str(plan_path),
                    "--srt-out", str(srt_path),
                ])
            self.assertEqual(code, 0, output.getvalue())
            plan_report = json.loads(plan_path.read_text(encoding="utf-8"))
            self.assertEqual(plan_report["data"]["source"]["subtitle_origin"], "generated_transcript")
            self.assertIn("生成字幕", srt_path.read_text(encoding="utf-8"))

    def test_cli_subtitle_generate_blocks_plain_text_transcript(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evidence_path = root / "waveform.json"
            transcript_path = root / "transcript.json"
            evidence_path.write_text(json.dumps({"duration_us": 1_000_000, "pauses": []}), encoding="utf-8")
            transcript_path.write_text(json.dumps({"segments": [{"id": "u1", "text": "没有时间"}]}), encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = roughcut_main([
                    "subtitle-generate",
                    "--audio", str(evidence_path),
                    "--transcript", str(transcript_path),
                ])
            self.assertEqual(code, 1)
            self.assertIn("start_us", output.getvalue())

    def test_timeline_mapping_hash_and_verified_gate(self):
        source = {"order": ["u1", "u2"]}
        target = {"order": ["u2", "u1"]}
        pending = compare_timeline_orders(source, target, [{"source": "u1", "target": "u2"}])
        self.assertEqual(pending["data"]["remap_status"], "pending")
        verified = compare_timeline_orders(source, target, [{"source": "u1", "target": "u2"}, {"source": "u2", "target": "u1"}])
        self.assertEqual(verified["data"]["remap_status"], "verified")
        bad_hash = compare_timeline_orders({"order": ["u1"], "order_hash": "sha256:wrong"}, {"order": ["u1"]})
        self.assertFalse(bad_hash["ok"])
        duplicate_target = compare_timeline_orders({"order": ["u1", "u2"]}, {"order": ["u2", "u3"]}, [{"source": "u1", "target": "u2"}, {"source": "u2", "target": "u2"}])
        self.assertFalse(duplicate_target["ok"])
        deleted_or_appended = compare_timeline_orders({"order": ["u1", "u2"]}, {"order": ["u2", "u3"]}, [{"source": "u2", "target": "u2"}])
        self.assertFalse(deleted_or_appended["ok"])
        self.assertEqual(deleted_or_appended["data"]["remap_status"], "pending")

    def test_material_status_is_not_promoted_and_precomputed_media_is_normalized(self):
        unknown = audit_material_completeness({"video": {"status": "unknown", "duration_us": 100}, "audio": {"status": "available", "duration_us": 100}, "transcript": {"status": "available", "metadata": {}}, "subtitle_timing": {"status": "available", "metadata": {}}})
        self.assertFalse(unknown["ok"])
        self.assertEqual(unknown["data"]["evidence"][0]["status"], "unknown")
        complete = audit_material_completeness({"video": {"status": "available", "duration_us": 100, "timebase": "microseconds"}, "audio": {"status": "available", "duration_us": 100}, "transcript": {"status": "available", "metadata": {}}, "subtitle_timing": {"status": "available", "metadata": {}}})
        self.assertTrue(complete["ok"], complete)
        self.assertEqual(complete["data"]["evidence"][0]["duration_us"], 100)

    def test_retrospective_reports_changed_missed_fully_adopted_and_confirmed_learning_only(self):
        proposal = {"decisions": [{"id": "d1", "action": "delete"}, {"id": "d2", "action": "keep"}]}
        final = {"workflow": {"content_pass": "stable"}, "decisions": [{"id": "d1", "action": "shorten"}, {"id": "d3", "action": "delete"}], "learning_feedback": {"dictionary_suggestions": [{"original": "错", "corrected": "对"}, {"original": "甲", "corrected": "乙", "human_confirmed": True}]}}
        report = build_retrospective_diff(proposal, final)
        self.assertTrue(report["ok"])
        self.assertEqual(report["summary"]["changed_count"], 1)
        self.assertEqual(report["summary"]["missed_count"], 1)
        self.assertEqual(report["data"]["dictionary_suggestions"], [{"original": "甲", "corrected": "乙", "human_confirmed": True}])
        zero = build_retrospective_diff({"workflow": {"content_pass": "approved"}, "decisions": [{"id": "d1", "action": "keep"}]}, {"workflow": {"content_pass": "approved"}, "decisions": [{"id": "d1", "action": "keep"}]})
        self.assertTrue(zero["data"]["fully_adopted"])
        incomplete = build_retrospective_diff({"decisions": [{"id": "d1", "action": "keep"}]}, {"workflow": {"content_pass": "approved"}})
        self.assertFalse(incomplete["ok"])
        self.assertFalse(incomplete["data"]["fully_adopted"])

    def test_rough_cli_output_options_and_input_errors(self):
        output = io.StringIO()
        playback = {"units": [{"id": "u1", "start_us": 0, "end_us": 100, "text": "内容"}]}
        with tempfile.TemporaryDirectory() as directory:
            map_path = Path(directory) / "map.json"
            map_path.write_text(json.dumps(playback, ensure_ascii=False), encoding="utf-8")
            with contextlib.redirect_stdout(output):
                code = roughcut_main(["scan", "--kind", "all", "--playback-map", str(map_path), "--format", "text"])
            self.assertEqual(code, 0)
            self.assertIn("candidate_scans", output.getvalue())
            self.assertEqual(roughcut_main(["scan", "--kind", "pauses", "--playback-map", str(map_path)]), 1)
            self.assertEqual(roughcut_main(["scan", "--kind", "all", "--playback-map", str(map_path), "--audio", "missing" + "." + "wav"]), 2)
            self.assertEqual(roughcut_main(["scan", "--kind", "all", "--playback-map", str(map_path), "--out", directory]), 2)


if __name__ == "__main__":
    unittest.main()
