from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_ROOT = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from roughcut_tool import main
from roughcut_tools.playback_map import build_playback_map
from roughcut_tools.subtitle_generation import build_generated_subtitle_units
from roughcut_tools.workflow import run_fixed_workflow


def whisperx_payload() -> dict:
    return {
        "result": {
            "text": "你好",
            "utterances": [
                {
                    "text": "你好",
                    "start": 1.25,
                    "end": 2.0,
                    "words": [
                        {"text": "你", "start_time": 1250, "end_time": 1500},
                        {"text": "好", "start_time": 1500, "end_time": 1900},
                    ],
                }
            ],
        },
        "validation": {"timing_valid": True, "warnings": []},
    }


class TranscriptImportTests(unittest.TestCase):
    def run_import(self, payload: dict) -> tuple[int, dict]:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "whisperx_result.json"
            source.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                code = main([
                    "import-transcript",
                    "--input", str(source),
                    "--format", "ai-jian-koubo-whisperx",
                ])
            return code, json.loads(stdout.getvalue())

    def test_import_converts_seconds_and_milliseconds_to_microseconds(self):
        code, report = self.run_import(whisperx_payload())

        self.assertEqual(code, 0, report)
        self.assertEqual(report["report_type"], "transcript_import")
        transcript = report["data"]
        segment = transcript["segments"][0]
        self.assertEqual(segment["id"], "segment-000001")
        self.assertEqual(segment["semantic_unit_id"], "segment-000001")
        self.assertEqual((segment["start_us"], segment["end_us"]), (1_250_000, 2_000_000))
        self.assertEqual(
            [(word["id"], word["start_us"], word["end_us"]) for word in segment["tokens"]],
            [
                ("token-000001-000001", 1_250_000, 1_500_000),
                ("token-000001-000002", 1_500_000, 1_900_000),
            ],
        )

    def test_generated_ids_are_stable_for_the_same_input(self):
        first_code, first = self.run_import(whisperx_payload())
        second_code, second = self.run_import(whisperx_payload())

        self.assertEqual((first_code, second_code), (0, 0))
        self.assertEqual(first["data"], second["data"])

    def test_import_cli_writes_a_workflow_ready_report_envelope(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "whisperx_result.json"
            output = Path(directory) / "canonical-transcript-report.json"
            source.write_text(json.dumps(whisperx_payload(), ensure_ascii=False), encoding="utf-8")
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                code = main([
                    "import-transcript", "--input", str(source),
                    "--format", "ai-jian-koubo-whisperx", "--out", str(output),
                ])

            report = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(code, 0, stdout.getvalue())
            self.assertEqual(report["report_type"], "transcript_import")
            self.assertIn("segments", report["data"])
            self.assertNotIn("transcript", report["data"])

    def test_imported_transcript_feeds_mapping_and_subtitle_generation(self):
        code, report = self.run_import(whisperx_payload())
        self.assertEqual(code, 0, report)
        transcript = report["data"]

        mapping = build_playback_map(transcript, {
            "segments": [{
                "id": "keep-1",
                "source_start_us": 0,
                "source_end_us": 2_000_000,
                "target_start_us": 0,
                "target_end_us": 2_000_000,
                "kept": True,
            }]
        })
        subtitles = build_generated_subtitle_units(transcript)

        self.assertTrue(mapping["ok"], mapping)
        self.assertTrue(subtitles["ok"], subtitles)
        self.assertEqual(mapping["data"]["units"][0]["text"], "你好")
        self.assertEqual(subtitles["data"]["subtitle_units"][0]["text"], "你好")

        workflow = run_fixed_workflow({
            "subtitle_mode": "generate",
            "subtitles": [],
            "transcript": report,
            "audio": {"duration_us": 2_000_000, "pauses": []},
        })
        self.assertTrue(workflow["ok"], workflow)
        self.assertIn("subtitle_generation", workflow["data"]["stages"])

    def test_missing_utterances_blocks_import(self):
        payload = whisperx_payload()
        payload["result"].pop("utterances")
        code, report = self.run_import(payload)

        self.assertNotEqual(code, 0)
        self.assertFalse(report["ok"])
        self.assertTrue(any("utterances" in error for error in report["errors"] + report["input_errors"]))

    def test_missing_word_timestamps_blocks_import(self):
        payload = whisperx_payload()
        payload["result"]["utterances"][0]["words"] = []
        code, report = self.run_import(payload)

        self.assertNotEqual(code, 0)
        self.assertFalse(report["ok"])
        self.assertTrue(any("word" in error.lower() for error in report["errors"] + report["input_errors"]))

    def test_invalid_upstream_timing_blocks_import(self):
        payload = whisperx_payload()
        payload["validation"]["timing_valid"] = False
        payload["validation"]["warnings"] = ["timestamp overlap"]
        code, report = self.run_import(payload)

        self.assertNotEqual(code, 0)
        self.assertFalse(report["ok"])
        self.assertTrue(any("timing_valid" in error for error in report["errors"] + report["input_errors"]))

    def test_negative_and_reversed_word_ranges_block_import(self):
        for start_time, end_time in ((-1, 100), (200, 100)):
            payload = whisperx_payload()
            payload["result"]["utterances"][0]["words"][0].update(
                start_time=start_time, end_time=end_time
            )
            with self.subTest(start_time=start_time, end_time=end_time):
                code, report = self.run_import(payload)
                self.assertNotEqual(code, 0)
                self.assertFalse(report["ok"])

    def test_content_mapping_and_generation_require_a_timed_transcript(self):
        for argv in (
            ["playback-map", "--edit-map", "missing-edit-map.json"],
            ["subtitle-generate", "--audio", "edited" + ".wav"],
        ):
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                code = main(argv)
            report = json.loads(stdout.getvalue())
            with self.subTest(argv=argv):
                self.assertNotEqual(code, 0)
                self.assertFalse(report["ok"])
                self.assertTrue(any("transcript" in error.lower() for error in report["input_errors"]))

    def test_existing_subtitle_alignment_can_run_without_a_transcript(self):
        report = run_fixed_workflow({
            "subtitle_mode": "existing",
            "subtitles": [{"id": "cue-1", "semantic_unit_id": "u1", "text": "已有字幕", "start_us": 100_000, "end_us": 500_000}],
            "audio": {"duration_us": 1_000_000, "pauses": []},
        })

        self.assertTrue(report["data"]["stages"]["subtitle_alignment"]["ok"])
        self.assertEqual(report["data"]["evidence_status"]["transcript"], "not_assessed")


if __name__ == "__main__":
    unittest.main()
