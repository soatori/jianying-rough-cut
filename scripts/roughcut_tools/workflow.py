"""Run the deterministic rough-cut preparation chain in one process.

The workflow is intentionally limited to evidence preparation and plan
generation.  Semantic choices, listening, approval, and all Jianying writes
remain human or belong to another skill after explicit handoff.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .candidate_scans import scan_all
from .io import BlockedReportError, load_json, unwrap_report
from .material_audit import audit_material_completeness
from .playback_map import build_playback_map
from .result import result
from .subtitle_generation import build_generated_subtitle_units
from .transcript_correction import apply_dictionary_corrections, load_dictionary
from .waveform import build_waveform_alignment_plan, extract_waveform_evidence

SUBTITLE_MODES = {"auto", "existing", "generate"}


def _value(value: Any) -> Any:
    if isinstance(value, (str, Path)) and str(value).lower().endswith((".json", ".jsonl")):
        return unwrap_report(load_json(value))
    return unwrap_report(value)


def _record(
    stages: dict[str, dict[str, Any]],
    name: str,
    report: dict[str, Any],
    errors: list[str],
    input_errors: list[str],
    warnings: list[str],
) -> None:
    # This labels deterministic preparation, not the supplied evidence or a verdict.
    report["provenance"] = "script_generated"
    stages[name] = report
    errors.extend(f"{name}: {item}" for item in report.get("errors", []))
    input_errors.extend(f"{name}: {item}" for item in report.get("input_errors", []))
    warnings.extend(f"{name}: {item}" for item in report.get("warnings", []))


def _workflow_payload(stages: dict[str, dict[str, Any]], artifacts: dict[str, Any], subtitle_mode: str | None) -> dict[str, Any]:
    return {
        "stages": stages,
        "artifacts": artifacts,
        "subtitle_mode": subtitle_mode,
        "manual_gates": [
            "transcript correction for unresolved technical terms",
            "semantic orientation and content-cut decisions",
            "human listening at every proposed waveform edge",
            "plan approval before any downstream editor handoff",
        ],
    }


def _workflow_summary(payload: dict[str, Any]) -> dict[str, Any]:
    stages = payload["stages"]
    provenance_counts = dict.fromkeys(
        ("script_generated", "agent_interpreted", "human_verified", "unavailable"), 0
    )
    for stage in stages.values():
        provenance_counts[stage.get("provenance", "unavailable")] += 1
    gates = payload["review_gates"]
    return {
        "stage_count": len(stages),
        "artifact_count": len(payload["artifacts"]),
        # Count the shared successful evidence stage, never its consumers.
        "waveform_passes": int(stages.get("waveform_evidence", {}).get("ok") is True),
        "provenance_counts": provenance_counts,
        "agent_required_count": len(payload["agent_required"]),
        "gate_counts": {
            "human_review": sum(gate["kind"] == "human_review" for gate in gates),
            "human_listening": sum(gate["kind"] == "human_listening" for gate in gates),
            "pending": sum(gate["status"] == "pending" for gate in gates),
            "cleared": sum(gate["status"] == "cleared" for gate in gates),
        },
        "blocked_stage_count": len(payload["blocked_work"]),
        "unavailable_evidence_count": sum(
            status == "unavailable" for status in payload["evidence_status"].values()
        ),
        "editor_writes": 0,
        "subtitle_mode": payload["subtitle_mode"] or "blocked",
    }


def _dictionary_values(value: Any) -> tuple[list[dict[str, str]], list[str]]:
    if value is None:
        return [], []
    if not isinstance(value, list):
        return [], ["dictionaries must be an array"]
    dictionaries: list[dict[str, str]] = []
    errors: list[str] = []
    for index, item in enumerate(value):
        try:
            dictionary = load_dictionary(item) if isinstance(item, (str, Path)) else item
        except (OSError, ValueError) as exc:
            errors.append(f"dictionary[{index}] could not be loaded: {exc}")
            continue
        if not isinstance(dictionary, dict):
            errors.append(f"dictionary[{index}] must be an object or JSON/Markdown path")
            continue
        dictionaries.append(dictionary)
    return dictionaries, errors


def _load_subtitle_input(bundle: dict[str, Any], inputs: Any) -> tuple[Any, bool, list[str]]:
    """Load subtitle units and retain whether their absence was explicit."""

    if "subtitles" in bundle:
        raw = bundle.get("subtitles")
        supplied = True
    elif isinstance(inputs, dict) and "subtitle_timing" in inputs:
        raw = inputs.get("subtitle_timing")
        supplied = True
    else:
        return None, False, []
    try:
        return _value(raw), supplied, []
    except (BlockedReportError, OSError, ValueError, TypeError, KeyError) as exc:
        return None, supplied, [f"subtitles: {exc}"]


def _resolve_subtitle_mode(
    requested: Any,
    subtitles: Any,
    subtitles_supplied: bool,
    transcript: Any,
) -> tuple[str | None, list[str]]:
    """Resolve subtitle mode without treating missing evidence as absence."""

    mode = "auto" if requested is None else requested
    if mode not in SUBTITLE_MODES:
        return None, [f"subtitle_mode must be one of {sorted(SUBTITLE_MODES)}"]

    has_subtitles = isinstance(subtitles, list) and bool(subtitles)
    explicit_no_subtitles = subtitles_supplied and isinstance(subtitles, list) and not subtitles
    transcript_available = transcript is not None

    if mode == "existing":
        if not has_subtitles:
            return None, ["subtitle_mode=existing requires a non-empty subtitles array"]
        return "existing", []

    if mode == "generate":
        if subtitles_supplied and not isinstance(subtitles, list):
            return None, [
                (
                    "subtitle_mode=generate requires subtitles to be absent or an explicit empty list; "
                    "the supplied subtitle state is unreadable or invalid"
                )
            ]
        if has_subtitles:
            return None, ["subtitle_mode=generate cannot run when existing subtitles are supplied"]
        if not transcript_available:
            return None, ["subtitle_mode=generate requires a timed transcript"]
        return "generate", []

    if has_subtitles:
        return "existing", []
    if explicit_no_subtitles and transcript_available:
        return "generate", []
    if explicit_no_subtitles:
        return None, ["subtitle_mode=auto found an explicit empty subtitle list but no timed transcript"]
    return None, [
        (
            "subtitle_mode=auto cannot determine whether subtitles are absent; "
            "supply subtitles: [] with a timed transcript or explicitly set subtitle_mode "
            "after a read-only subtitle-state probe"
        )
    ]


def run_fixed_workflow(bundle: Any) -> dict[str, Any]:
    """Run the repeatable prep steps without invoking an editor adapter.

    Bundle keys are intentionally generic: ``inputs``, ``transcript``,
    ``edit_map``, ``subtitles``, ``subtitle_mode``, ``audio``, ``dictionaries``,
    ``preferences`` and ``pause_config``.  ``subtitle_mode`` is ``auto`` by
    default and may be forced to ``existing`` or ``generate``.  ``audio`` may
    be a path or precomputed waveform evidence.  ``playback_map`` may be
    supplied when the edit mapping was already verified.
    """

    if not isinstance(bundle, dict):
        return result("roughcut_workflow", input_errors=["workflow bundle must be a JSON object"])

    stages: dict[str, dict[str, Any]] = {}
    artifacts: dict[str, Any] = {}
    errors: list[str] = []
    input_errors: list[str] = []
    warnings: list[str] = []
    transcript_corrections: list[dict[str, Any]] = []

    subtitle_mode: str | None = None
    inputs = bundle.get("inputs")
    raw_subtitles = bundle.get("subtitles") if "subtitles" in bundle else (
        inputs.get("subtitle_timing") if isinstance(inputs, dict) else None
    )
    generation_requested = bundle.get("subtitle_mode") == "generate" or (
        bundle.get("subtitle_mode", "auto") in {None, "auto"} and raw_subtitles == []
    )
    evidence_status = {
        "audio": "unavailable",
        "transcript": "not_assessed" if bundle.get("transcript") is not None or not (
            generation_requested or bundle.get("edit_map") is not None
        ) else "unavailable",
        "subtitle_state": "unavailable",
        "playback_map": "unavailable",
    }

    def finish() -> dict[str, Any]:
        payload = _workflow_payload(stages, artifacts, subtitle_mode)
        payload["evidence_status"] = evidence_status
        payload["agent_required"] = [
            "interpret unresolved transcript terms and protected facts",
            "orient semantic units and audit content relationships",
            "classify pause functions and assess semantic risk in context",
        ]
        payload["review_gates"] = [
            {"id": name, "kind": kind, "status": "pending", "provenance": "unavailable"}
            for name, kind in (
                ("transcript_terms", "human_review"),
                ("content_decisions", "human_review"),
                ("waveform_edges", "human_listening"),
                ("plan_approval", "human_review"),
            )
        ]
        required = {"waveform_evidence", "candidate_scans", "subtitle_alignment"}
        if generation_requested or subtitle_mode == "generate":
            required.add("subtitle_generation")
        blocked_work = {
            name for name in required | set(stages)
            if not stages.get(name, {}).get("ok")
        }
        scan_data = stages.get("candidate_scans", {}).get("data") or {}
        if scan_data.get("pause_scan_status") == "not_executed":
            # Text scans can succeed while their audio-dependent substage is blocked.
            blocked_work.add("candidate_scans.pause_scan")
        payload["blocked_work"] = sorted(blocked_work)
        return result(
            "roughcut_workflow", data=payload, errors=errors, input_errors=input_errors,
            warnings=warnings, summary=_workflow_summary(payload),
        )

    if inputs is not None:
        try:
            audit = audit_material_completeness(_value(inputs))
        except (OSError, ValueError, TypeError, KeyError) as exc:
            audit = result("material_completeness", input_errors=[str(exc)])
        _record(stages, "material_audit", audit, errors, input_errors, warnings)
        artifacts["material_audit"] = audit.get("data")

    transcript = bundle.get("transcript")
    if transcript is not None:
        try:
            transcript = _value(transcript)
        except (OSError, ValueError, TypeError, KeyError) as exc:
            transcript = None
            errors.append(f"transcript: {exc}")

    if bundle.get("transcript") is not None:
        evidence_status["transcript"] = "available" if transcript is not None else "unavailable"

    if transcript is not None and "dictionaries" in bundle:
        dictionaries, dictionary_errors = _dictionary_values(bundle.get("dictionaries"))
        if dictionary_errors:
            correction = result("transcript_correction", errors=dictionary_errors)
        else:
            correction = apply_dictionary_corrections(transcript, dictionaries)
        _record(stages, "transcript_correction", correction, errors, input_errors, warnings)
        if correction.get("ok"):
            transcript = correction["data"]["transcript"]
            transcript_corrections = correction["data"].get("corrections", [])
            artifacts["transcript"] = transcript

    subtitles, subtitles_supplied, subtitle_load_errors = _load_subtitle_input(bundle, inputs)
    input_errors.extend(subtitle_load_errors)
    if subtitles_supplied and subtitles == [] and bundle.get("subtitle_mode", "auto") in {None, "auto"}:
        generation_requested = True
        if transcript is None:
            evidence_status["transcript"] = "unavailable"
    if subtitles_supplied and isinstance(subtitles, list) and not subtitle_load_errors:
        evidence_status["subtitle_state"] = "available"
    elif bundle.get("subtitle_mode") == "generate" and not subtitles_supplied:
        # An explicit generate request declares an absent subtitle state.
        evidence_status["subtitle_state"] = "available"
    subtitle_mode, mode_errors = _resolve_subtitle_mode(
        bundle.get("subtitle_mode"),
        subtitles,
        subtitles_supplied,
        transcript,
    )
    if mode_errors:
        input_errors.extend(mode_errors)
        warnings.append("workflow stopped before waveform analysis because subtitle mode could not be resolved")
        return finish()

    # A failed or unreadable subtitle-state input is not evidence that the
    # timeline is empty. Even an explicit generate request must not override
    # that uncertainty; the caller needs to provide an absent/empty state
    # explicitly after a read-only probe.
    if subtitle_load_errors:
        warnings.append("workflow stopped before generation and waveform analysis because subtitle state could not be read")
        return finish()

    audio = bundle.get("audio")
    if audio is None and isinstance(inputs, dict):
        audio = inputs.get("audio")
    try:
        audio = _value(audio) if audio is not None else None
    except (BlockedReportError, OSError, ValueError, TypeError, KeyError) as exc:
        audio = None
        input_errors.append(f"audio: {exc}")
    if audio is None:
        evidence_status["audio"] = "unavailable"
        input_errors.append("subtitle alignment requires edited-timeline audio or precomputed waveform evidence")
        warnings.append("workflow stopped before generation and waveform analysis because edited audio evidence is missing")
        return finish()

    pause_config = bundle.get("pause_config")
    if pause_config is not None and not isinstance(pause_config, dict):
        errors.append("pause_config must be an object")
        pause_config = None

    subtitle_source_metadata: dict[str, Any] = {}
    if subtitle_mode == "generate":
        generation = build_generated_subtitle_units(transcript, transcript_corrections)
        _record(stages, "subtitle_generation", generation, errors, input_errors, warnings)
        if generation.get("ok"):
            evidence_status["transcript"] = "available"
            generated_data = generation.get("data") or {}
            subtitles = generated_data.get("subtitle_units")
            artifacts["generated_subtitles"] = subtitles
            subtitle_source_metadata = {
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
        else:
            evidence_status["transcript"] = "unavailable"
            warnings.append("workflow stopped before waveform analysis because timed transcript generation was blocked")
            return finish()

    playback: Any = bundle.get("playback_map")
    if playback is not None:
        try:
            playback = _value(playback)
        except (OSError, ValueError, TypeError, KeyError) as exc:
            playback = None
            errors.append(f"playback_map: {exc}")
    elif transcript is not None and bundle.get("edit_map") is not None:
        try:
            playback = build_playback_map(transcript, _value(bundle["edit_map"]))
            _record(stages, "playback_map", playback, errors, input_errors, warnings)
            if playback.get("ok"):
                playback = playback.get("data")
                artifacts["playback_map"] = playback
        except (OSError, ValueError, TypeError, KeyError) as exc:
            playback = None
            errors.append(f"playback_map: {exc}")

    waveform_data: dict[str, Any] | None = None
    if audio is not None:
        waveform = extract_waveform_evidence(audio, pause_config)
        _record(stages, "waveform_evidence", waveform, errors, input_errors, warnings)
        evidence_status["audio"] = "available" if waveform.get("ok") else "unavailable"
        if waveform.get("ok"):
            waveform_data = waveform.get("data")
            artifacts["waveform_evidence"] = waveform_data

    if playback is not None:
        try:
            playback_data = _value(playback)
        except (BlockedReportError, OSError, ValueError, TypeError, KeyError) as exc:
            playback_data = None
            warnings.append(f"candidate_scans: skipped because playback map is blocked: {exc}")
        if isinstance(playback_data, dict) and playback_data.get("mapping_status") in {None, "verified"} and not playback_data.get("unmapped_token_ids"):
            # Do not retry ffmpeg after the waveform stage has failed.  A
            # failed audio pass is already a safety block, and retrying it
            # only repeats the slow operation without adding evidence.
            scans = scan_all(playback_data, bundle.get("preferences"), waveform_data, pause_config)
            _record(stages, "candidate_scans", scans, errors, input_errors, warnings)
            evidence_status["playback_map"] = "available" if scans.get("ok") else "unavailable"
            artifacts["candidate_scans"] = scans.get("data")
        elif playback_data is not None:
            warnings.append("candidate_scans: skipped because playback mapping is unresolved")
    else:
        warnings.append("candidate_scans: skipped because no playback map was supplied")

    if subtitle_mode and subtitles is not None and waveform_data is not None:
        try:
            alignment = build_waveform_alignment_plan(
                waveform_data,
                subtitles,
                pause_config,
                text_authority="generated_transcript" if subtitle_mode == "generate" else "current_visible_subtitle",
                subtitle_origin="generated_transcript" if subtitle_mode == "generate" else "current_timeline",
                source_metadata=subtitle_source_metadata,
            )
            _record(stages, "subtitle_alignment", alignment, errors, input_errors, warnings)
            artifacts["subtitle_alignment"] = alignment.get("data")
        except (BlockedReportError, OSError, ValueError, TypeError, KeyError) as exc:
            errors.append(f"subtitle_alignment: {exc}")
    elif subtitle_mode and subtitles is not None:
        warnings.append("subtitle_alignment: skipped because waveform evidence is unavailable")

    warnings.extend([
        "semantic orientation, content decisions, waveform-edge listening, and approval remain human gates",
        "this workflow never invokes jianying-editor and never writes a Jianying draft",
    ])
    return finish()
