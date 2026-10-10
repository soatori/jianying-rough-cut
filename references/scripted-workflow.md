# Script-first rough-cut workflow

Use the CLI for deterministic preparation. Keep semantic judgment, technical
listening, and approval as explicit human gates.

Stage map: the Material, Transcript, and Edited-time rows are **粗剪**
preparation (structure and evidence); the Cleanup-candidates and both subtitle
rows are **精剪** (the delivery-refinement loop and subtitle alignment). Here
"script-first" means *CLI-script-first* deterministic prep, unrelated to whether
the speaker had a written 文案 — the 文案 / 无文案 choice lives in the copy-first
and discovery runbooks.

When the request is subtitle-only, select the `subtitle_alignment` operating
mode. Do not run the full content-edit route just to align or generate
subtitles. The input must identify edited-timeline audio (or precomputed
waveform evidence); missing or unreadable audio blocks before generation and
before FFmpeg. In `auto`, missing or unreadable subtitle state also blocks;
explicit `generate` may omit `subtitles` or provide `subtitles: []`, but
must block if a supplied subtitle-state object cannot be read.

| Stage | Script action | Agent-required follow-up | Human gate |
|---|---|---|---|
| Material | `preflight` or the `workflow` bundle stage | interpret completeness limits without inventing missing evidence | confirm that missing/partial evidence is acceptable |
| Transcript | `correct-transcript` with confirmed dictionaries | review unresolved terminology and protected facts | listen to unresolved names, numbers, models, and conditions |
| Edited time | `playback-map` from the approved edit map | inspect semantic membership/order and mapping limits | confirm order/remap is verified |
| Cleanup candidates | `scan --kind all` or the `workflow` bundle stage | classify pause functions and semantic risk in context | listen in context; candidates never mean delete |
| Existing subtitles | `subtitle-align` or `workflow --subtitle-mode existing` | cross-check wording and boundary evidence | preserve current text/order/segmentation; listen to every flagged edge |
| No subtitles | `subtitle-generate` or `workflow --subtitle-mode generate` | proofread generated units and unresolved terms | listen to generated text and every flagged edge; approve the plan and SRT |
| Retrospective | `retrospective` | separate reusable lessons from case-specific records | record only corrections the user actually accepted |

## Two subtitle modes

The subtitle path has two explicit modes. `existing` treats the current visible
subtitle units as authoritative for wording, order, and segmentation; waveform
analysis only supplies boundary candidates and review evidence. `generate` is
used only when the timeline has no subtitles and a timed transcript is
available. It corrects text, keeps the transcript's token/segment times, then
uses the edited-timeline waveform to build a review-pending alignment plan.

`auto` is fail-closed: a non-empty `subtitles` input selects `existing`; an
explicit `subtitles: []` together with a timed transcript selects `generate`.
Missing or unreadable subtitle-state evidence is not treated as “no subtitles”;
the report asks for an explicit mode or a read-only subtitle-state probe. An
explicit `generate` request with non-empty subtitles is blocked. Plain text
without `segment`/`word` timestamps is not a valid generation input.

## High-precision subtitle command

```powershell
python scripts/roughcut_tool.py subtitle-align `
  --audio "<edited-audio.wav>" `
  --subtitles "<current-subtitles.json>" `
  --out "<subtitle-alignment-plan.json>"
```

`subtitle-align` runs one waveform pass with `ffmpeg silencedetect` and uses
the detected pause edges to produce review-pending candidates. It never uses
ASR word timestamps as the boundary authority. If word timings are present,
they are reported as `words_health.role=cross_check` only. By default the
saved manual range is retained and the nearby waveform edge is recorded as a
candidate. Only an explicit config with
`auto_snap_within_tolerance=true` may snap a boundary inside the tolerance;
larger offsets always retain the saved boundary and carry a listening flag.

The current subtitle text and segmentation are input evidence, not a rebuild
source. The command does not restore an older script order, overwrite wording,
or emit Jianying IDs or write instructions.

For a timeline with no subtitles, generate a plan and an UTF-8 SRT review
artifact from a timed external/local transcript:

```powershell
python scripts/roughcut_tool.py subtitle-generate `
  --audio "<edited-audio.wav>" `
  --transcript "<timed-transcript.json>" `
  --dictionary "<confirmed-dictionary.json>" `
  --out "<subtitle-generation-plan.json>" `
  --srt-out "<subtitle-preview.srt>"
```

Dictionary correction changes wording only; it never changes transcript
timestamps, token identity, or semantic units. `subtitle-generate` runs one
waveform pass and reuses it while building the alignment candidates. The SRT
is for preview and review only; it is not a Jianying write-back source. By
default, waveform edges remain candidates and the supplied saved/transcript
range remains selected; an explicit snap configuration or later human approval
is required before a candidate becomes the selected boundary. Both paths keep
`review_status=pending` until a person listens to the result.

## One-shot deterministic preparation

When transcript, edit map, current subtitle units, and edited audio are already
available as application-independent JSON, place them in one `workflow` bundle
and run:

```powershell
python scripts/roughcut_tool.py workflow \
  --input "<roughcut-workflow.json>" \
  --subtitle-mode auto \
  --out "<roughcut-workflow-report.json>"
```

The CLI flag overrides the bundle's `subtitle_mode`; omitting it preserves the
bundle value. Add `--srt-out "<subtitle-preview.srt>"` when the selected
workflow path is expected to produce a subtitle alignment plan.

The bundle may contain `inputs`, `transcript`, `edit_map`, `subtitles`, `audio`,
`dictionaries`, `preferences`, `pause_config`, and `subtitle_mode`. For
`subtitle_mode=existing`, `subtitles` must be non-empty. For
`subtitle_mode=generate`, `subtitles` must be absent or explicitly empty and
`transcript` must contain timed segments or words. With `subtitle_mode=auto`,
use a non-empty subtitle list for the existing path or an explicit empty list
plus timed transcript for the generation path; otherwise the workflow blocks
because the subtitle state is unknown.

The workflow reuses the single waveform result for pause scanning and subtitle
alignment, so it does not invoke ffmpeg again for the candidate scan. It never
invokes `jianying-editor`, reads a Jianying project, or writes a Jianying draft.

## Coverage summary and pending work

The `workflow` summary is coverage metadata, not completed semantic work or
completed human review. Its counts describe this preparation run only:

| Field | Counting unit and limit |
|---|---|
| `stage_count` | Recorded deterministic stage reports, including failed attempts; skipped stages are excluded. |
| `artifact_count` | Artifact entries emitted by stages; inspect stage status before consuming them. |
| `waveform_passes` | Successful shared waveform-evidence stage: zero or one. Precomputed evidence counts once; scans and alignment reuse it. This is not the number of FFmpeg calls, normalizations, or failed attempts. |
| `provenance_counts` | Top-level stage reports by `script_generated`, `agent_interpreted`, `human_verified`, or `unavailable`. Each stage explicitly labels its deterministic preparation as `script_generated`, including failed reports; this does not relabel its input evidence or mean its contents were reviewed. Agent/human counts remain zero. |
| `agent_required_count` | Three declared follow-up categories in `data.agent_required`: transcript interpretation, semantic orientation/audit, and contextual pause/risk assessment. Categories are requirements, not completed actions or per-candidate counts. |
| `gate_counts` | Four declared gates in `data.review_gates`: three `human_review` and one `human_listening`. All four remain `pending`; `cleared` is zero. Counts are gate categories, not reviewed rows or listened-to edges. |
| `blocked_stage_count` | Unique names in `data.blocked_work`: failed recorded stages plus unexecuted waveform, candidate-scan, and alignment work; generation is included when requested or selected. A skipped downstream stage is counted once even with several missing prerequisites. |
| `unavailable_evidence_count` | Unavailable entries in `data.evidence_status`, counted once per evidence category rather than per error or affected stage. |

`data.evidence_status` distinguishes audio, transcript, subtitle state, and
playback mapping. `available` means readable/accepted at the relevant
preparation step, not semantically correct or human-verified. Required evidence
that is missing, unreadable, unresolved, or cannot be evaluated after an upstream
block is `unavailable`. An omitted transcript is `not_assessed` when generation
and source-to-edited mapping do not require it. A supplied playback map still
needs usable canonical units; unresolved mappings never run candidate scans.
An explicit empty subtitle list is evidence of absence, not missing evidence.

Missing audio or unknown subtitle state stops alignment preparation. Missing
transcript blocks generation and source-to-edited mapping; an already supplied
usable playback map does not require another transcript. Missing or unresolved
mapping blocks candidate scans while existing-subtitle waveform alignment may
continue. Thus `ok=true` can coexist with blocked optional content-scan work;
inspect both stage records and `blocked_work` before choosing a handoff. Early
returns retain the same coverage fields, and no evidence count clears a gate.

Agent interpretation must supply contextual reasoning and provenance separately.
Neither ASR, a long pause, a waveform edge, nor a successful CLI run authorizes
deleting, splitting, joining, or removing a pause. Semantic membership/order or
protected-fact changes return to rough-cut review. A recorded human verdict is
required to clear `human_listening`; agent playback cannot clear it. This
workflow does not ingest verdicts or advance review states automatically.

If a saved draft must be probed, resolved, cloned, or written back, stop at
this skill boundary and ask for explicit confirmation before involving
`jianying-editor`.
