#!/usr/bin/env python3
"""Application-independent rough-cut analysis CLI.

This command produces evidence, candidates and plans. It never writes a
Jianying project and never turns a candidate into an automatic delete.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from roughcut_tools.candidate_scans import (
    detect_english_stutter_candidates,
    detect_false_start_candidates,
    detect_filler_candidates,
    detect_misspoken_retake_candidates,
    detect_pause_candidates,
    detect_repetition_candidates,
    scan_all,
)
from roughcut_tools.io import (
    BlockedReportError,
    dump_json,
    load_json,
    text_result,
    unwrap_report,
    write_json,
)
from roughcut_tools.material_audit import audit_material_completeness
from roughcut_tools.generic_content import check_generic_content
from roughcut_tools.learning import build_learning_report, validate_learning_report
from roughcut_tools.playback_map import build_playback_map
from roughcut_tools.result import exit_code, result
from roughcut_tools.retrospective import build_retrospective_diff
from roughcut_tools.review_snippets import build_review_snippets
from roughcut_tools.subtitle_alignment import build_subtitle_alignment_plan
from roughcut_tools.subtitle_generation import (
    build_generated_subtitle_units,
    render_srt,
)
from roughcut_tools.timeline_compare import build_stage_diff, compare_timeline_orders
from roughcut_tools.transcript_correction import (
    apply_dictionary_corrections,
    load_dictionary,
)
from roughcut_tools.validators import (
    validate_alignment_plan,
    validate_analysis_report,
    validate_decision_plan,
)
from roughcut_tools.validators.stage_comparison_report import validate_stage_comparison_report
from roughcut_tools.waveform import build_waveform_alignment_plan
from roughcut_tools.workflow import run_fixed_workflow


def _validated(report_type: str, value: dict[str, Any]) -> dict[str, Any]:
    return result(report_type, data=value, errors=value.get("errors", []), input_errors=value.get("input_errors", []), warnings=value.get("warnings", []), summary={key: value[key] for key in value if key.endswith("_count")})


def _subtitle_generation_report(args: argparse.Namespace) -> dict[str, Any]:
    transcript = unwrap_report(load_json(args.transcript))
    corrections: list[dict[str, Any]] = []
    if args.dictionary:
        dictionaries = [load_dictionary(path) for path in args.dictionary]
        correction = apply_dictionary_corrections(transcript, dictionaries)
        if not correction["ok"]:
            return result(
                "subtitle_alignment_plan",
                data={"subtitle_generation": correction.get("data")},
                errors=correction.get("errors", []),
                input_errors=correction.get("input_errors", []),
                warnings=correction.get("warnings", []),
            )
        transcript = correction["data"]["transcript"]
        corrections = correction["data"].get("corrections", [])

    generated = build_generated_subtitle_units(transcript, corrections)
    if not generated["ok"]:
        return result(
            "subtitle_alignment_plan",
            data={"subtitle_generation": generated.get("data")},
            errors=generated.get("errors", []),
            input_errors=generated.get("input_errors", []),
            warnings=generated.get("warnings", []),
        )
    generated_data = generated["data"]
    source_metadata = {
        "segmentation_source": (generated_data.get("source") or {}).get(
            "segmentation_source", "timed_transcript_segments"
        ),
        "text_source": (generated_data.get("source") or {}).get(
            "text_source", "corrected_timed_transcript"
        ),
        "unresolved_terms": generated_data.get("unresolved_terms", []),
        "correction_count": len(generated_data.get("corrections", [])),
        "generated_from": "timed_transcript",
    }
    alignment = build_waveform_alignment_plan(
        _load_audio_input(args.audio),
        generated_data["subtitle_units"],
        load_json(args.config) if args.config else None,
        text_authority="generated_transcript",
        subtitle_origin="generated_transcript",
        source_metadata=source_metadata,
    )
    alignment["warnings"] = [*generated.get("warnings", []), *alignment.get("warnings", [])]
    if alignment["warnings"] and alignment.get("status") == "ok":
        alignment["status"] = "review"
    alignment["summary"]["generated_subtitle_unit_count"] = len(generated_data["subtitle_units"])
    return alignment


def _alignment_plan_for_srt(report: dict[str, Any]) -> dict[str, Any] | None:
    if report.get("report_type") == "subtitle_alignment_plan" and isinstance(report.get("data"), dict):
        return report["data"]
    if report.get("report_type") == "roughcut_workflow":
        data = report.get("data")
        if isinstance(data, dict):
            artifacts = data.get("artifacts")
            if isinstance(artifacts, dict) and isinstance(artifacts.get("subtitle_alignment"), dict):
                return artifacts["subtitle_alignment"]
    return None


def _run(args: argparse.Namespace) -> dict[str, Any]:
    if args.command == "validate":
        if args.kind == "comparison-report":
            return validate_stage_comparison_report(unwrap_report(load_json(args.path)))
        if args.kind == "plan":
            return _validated("decision_plan_validation", validate_decision_plan(unwrap_report(load_json(args.path))))
        if args.kind == "alignment":
            return _validated("alignment_plan_validation", validate_alignment_plan(unwrap_report(load_json(args.path))))
        if args.kind == "report":
            return _validated("analysis_report_validation", validate_analysis_report(unwrap_report(load_json(args.path))))
        if args.kind == "learning":
            return _validated("learning_report_validation", validate_learning_report(unwrap_report(load_json(args.path))))
        if args.kind == "generic":
            return _validated("roughcut_generic_content_validation", check_generic_content(args.paths, args.forbid))

    if args.command == "preflight":
        inputs = {"video": args.video, "audio": args.audio, "transcript": args.transcript, "subtitle_timing": args.subtitle_timing}
        inputs = {key: value for key, value in inputs.items() if value}
        return audit_material_completeness(inputs)

    if args.command == "correct-transcript":
        dictionaries = [load_dictionary(path) for path in args.dictionary]
        return apply_dictionary_corrections(unwrap_report(load_json(args.transcript)), dictionaries)

    if args.command == "playback-map":
        return build_playback_map(unwrap_report(load_json(args.transcript)), unwrap_report(load_json(args.edit_map)))

    if args.command == "scan":
        playback = unwrap_report(load_json(args.playback_map), "playback_map")
        if not isinstance(playback, dict) or not isinstance(playback.get("units"), list):
            return result("candidate_scans", errors=["playback map must contain canonical units"], status="blocked")
        if playback.get("mapping_status") not in {None, "verified"} or playback.get("unmapped_token_ids"):
            return result("candidate_scans", errors=["playback map is unresolved; candidate scanning is blocked"], status="blocked")
        preferences = load_json(args.preferences) if args.preferences else None
        if args.kind == "all":
            audio = _load_audio_input(args.audio) if args.audio else None
            pause_config = load_json(args.pause_config) if args.pause_config else None
            return scan_all(playback, preferences, audio, pause_config)
        functions = {
            "repetition": detect_repetition_candidates,
            "false-start": detect_false_start_candidates,
            "retake": detect_misspoken_retake_candidates,
            "english-stutter": detect_english_stutter_candidates,
            "fillers": lambda value: detect_filler_candidates(value, preferences),
            "pauses": lambda value: detect_pause_candidates(_load_audio_input(args.audio) if args.audio else None, load_json(args.pause_config) if args.pause_config else None),
        }
        return functions[args.kind](playback)

    if args.command == "review-snippets":
        if args.media.endswith((".json", ".jsonl")):
            media = unwrap_report(load_json(args.media))
        else:
            if not Path(args.media).exists():
                raise FileNotFoundError(f"media path does not exist: {args.media}")
            media = {"path": args.media}
        return build_review_snippets(unwrap_report(load_json(args.candidates)), media)

    if args.command == "build-alignment":
        return build_subtitle_alignment_plan(unwrap_report(load_json(args.map), "playback_map"), unwrap_report(load_json(args.subtitles)))

    if args.command == "subtitle-align":
        return build_waveform_alignment_plan(_load_audio_input(args.audio), unwrap_report(load_json(args.subtitles)), load_json(args.config) if args.config else None)

    if args.command == "subtitle-generate":
        return _subtitle_generation_report(args)

    if args.command == "workflow":
        bundle = unwrap_report(load_json(args.input))
        if args.subtitle_mode is not None:
            if not isinstance(bundle, dict):
                return result("roughcut_workflow", input_errors=["workflow bundle must be an object"])
            bundle = dict(bundle)
            bundle["subtitle_mode"] = args.subtitle_mode
        return run_fixed_workflow(bundle)

    if args.command == "compare":
        mapping = unwrap_report(load_json(args.mapping)) if args.mapping else None
        return compare_timeline_orders(unwrap_report(load_json(args.source)), unwrap_report(load_json(args.target)), mapping)

    if args.command == "stage-diff":
        mapping = unwrap_report(load_json(args.mapping)) if args.mapping else None
        exclusions = unwrap_report(load_json(args.exclusions)) if args.exclusions else None
        return build_stage_diff(
            unwrap_report(load_json(args.source)),
            unwrap_report(load_json(args.target)),
            mapping,
            exclusions,
        )

    if args.command == "learning-report":
        entries = unwrap_report(load_json(args.entries))
        return build_learning_report(entries, source_kind=args.source_kind, case_ref=args.case_ref)

    if args.command == "retrospective":
        return build_retrospective_diff(unwrap_report(load_json(args.proposal)), unwrap_report(load_json(args.final)))

    raise ValueError(f"unsupported command: {args.command}")


def _load_audio_input(path: str | None) -> Any:
    if not path:
        return None
    if path.endswith((".json", ".jsonl")):
        return unwrap_report(load_json(path))
    if not Path(path).exists():
        raise FileNotFoundError(f"audio path does not exist: {path}")
    return path


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise ValueError(f"argument error: {message}")


def _normalize_output_options(argv: list[str] | None) -> list[str] | None:
    """Allow output options before or after the subcommand."""
    if argv is None:
        return None
    leading: list[str] = []
    remaining: list[str] = []
    index = 0
    while index < len(argv):
        token = argv[index]
        if token in {"--format", "--out"} and index + 1 < len(argv):
            leading.extend((token, argv[index + 1]))
            index += 2
            continue
        if token.startswith(("--format=", "--out=")):
            leading.append(token)
            index += 1
            continue
        remaining.append(token)
        index += 1
    return leading + remaining


def _parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=("json", "text"), default="json")
    parser.add_argument("--out", help="write the complete report to this path")
    sub = parser.add_subparsers(dest="command", required=True)

    validate = sub.add_parser("validate")
    validate_sub = validate.add_subparsers(dest="kind", required=True)
    for kind in ("plan", "alignment", "report", "learning", "comparison-report"):
        item = validate_sub.add_parser(kind)
        item.add_argument("path")
    generic = validate_sub.add_parser("generic")
    generic.add_argument("paths", nargs="+")
    generic.add_argument("--forbid", action="append", default=[])

    preflight = sub.add_parser("preflight")
    preflight.add_argument("--video")
    preflight.add_argument("--audio")
    preflight.add_argument("--transcript")
    preflight.add_argument("--subtitle-timing")

    correction = sub.add_parser("correct-transcript")
    correction.add_argument("--transcript", required=True)
    correction.add_argument("--dictionary", action="append", required=True)

    playback = sub.add_parser("playback-map")
    playback.add_argument("--transcript", required=True)
    playback.add_argument("--edit-map", required=True)

    scan = sub.add_parser("scan")
    scan.add_argument("--kind", choices=("all", "repetition", "false-start", "retake", "english-stutter", "fillers", "pauses"), required=True)
    scan.add_argument("--playback-map", required=True)
    scan.add_argument("--preferences")
    scan.add_argument("--pause-config")
    scan.add_argument("--audio")

    snippets = sub.add_parser("review-snippets")
    snippets.add_argument("--candidates", required=True)
    snippets.add_argument("--media", required=True)

    alignment = sub.add_parser("build-alignment")
    alignment.add_argument("--map", required=True)
    alignment.add_argument("--subtitles", required=True)

    waveform_alignment = sub.add_parser("subtitle-align")
    waveform_alignment.add_argument("--audio", required=True, help="edited audio path or precomputed waveform evidence JSON")
    waveform_alignment.add_argument("--subtitles", required=True, help="current saved subtitle units JSON")
    waveform_alignment.add_argument("--config", help="optional waveform detector config JSON")

    waveform_generation = sub.add_parser("subtitle-generate")
    waveform_generation.add_argument("--audio", required=True, help="edited audio path or precomputed waveform evidence JSON")
    waveform_generation.add_argument("--transcript", required=True, help="timed transcript JSON with segments or units")
    waveform_generation.add_argument("--dictionary", action="append", help="optional confirmed dictionary JSON/Markdown path")
    waveform_generation.add_argument("--config", help="optional waveform detector config JSON")
    waveform_generation.add_argument("--srt-out", help="optional UTF-8 SRT preview output path")

    workflow = sub.add_parser("workflow")
    workflow.add_argument("--input", required=True, help="generic rough-cut workflow bundle JSON")
    workflow.add_argument("--subtitle-mode", choices=("auto", "existing", "generate"), help="override the bundle subtitle_mode")
    workflow.add_argument("--srt-out", help="optional UTF-8 SRT preview output path")

    compare = sub.add_parser("compare")
    compare.add_argument("--source", required=True)
    compare.add_argument("--target", required=True)
    compare.add_argument("--mapping")

    stage_diff = sub.add_parser("stage-diff")
    stage_diff.add_argument("--source", required=True)
    stage_diff.add_argument("--target", required=True)
    stage_diff.add_argument("--mapping")
    stage_diff.add_argument("--exclusions", help="JSON array of excluded compound intervals")

    learning = sub.add_parser("learning-report")
    learning.add_argument("--entries", required=True)
    learning.add_argument("--source-kind", choices=("project_case", "synthetic_fixture", "manual_review"), default="project_case")
    learning.add_argument("--case-ref")

    retrospective = sub.add_parser("retrospective")
    retrospective.add_argument("--proposal", required=True)
    retrospective.add_argument("--final", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args: argparse.Namespace | None = None
    try:
        raw_argv = sys.argv[1:] if argv is None else argv
        args = _parser().parse_args(_normalize_output_options(raw_argv))
        report = _run(args)
    except BlockedReportError as exc:
        report = result("roughcut_cli", errors=[f"blocked input report: {exc}"], status="blocked")
        code = 1
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        report = result("roughcut_cli", input_errors=[f"input error: {type(exc).__name__}: {exc}"], status="blocked")
        code = 2
    else:
        code = exit_code(report)
    output_format = getattr(args, "format", "json")
    srt_path = getattr(args, "srt_out", None)
    if srt_path:
        try:
            if not report.get("ok"):
                raise ValueError("cannot write SRT from a blocked subtitle report")
            alignment_plan = _alignment_plan_for_srt(report)
            if alignment_plan is None:
                raise ValueError("SRT output requires a subtitle alignment plan")
            Path(srt_path).write_text(render_srt(alignment_plan), encoding="utf-8")
        except (OSError, ValueError, TypeError) as exc:
            report = result(
                "roughcut_cli",
                data={"report": report},
                input_errors=[f"SRT output error: {exc}"],
                status="blocked",
            )
            code = 2
            output_format = "json"
    output_path = getattr(args, "out", None)
    if output_path:
        try:
            write_json(output_path, report)
        except OSError as exc:
            report = result("roughcut_cli", data={"report": report}, input_errors=[f"output error: {exc}"], status="blocked")
            code = 2
            output_format = "json"
    print(text_result(report) if output_format == "text" else dump_json(report))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
