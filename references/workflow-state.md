# Three-skill workflow state

The skills share these handoff states:

| State | Allowed values | Owner | Meaning |
|---|---|---|---|
| `content_pass` | `draft`, `stable`, `approved` | `jianying-rough-cut` | the semantic rough-cut decisions and plan are at the stated review level; `jianying-editor` owns project execution |
| `subtitle_alignment` | `not_started`, `draft`, `stable`, `approved` | `jianying-rough-cut` | current visible subtitles or generated timed-transcript units have been checked against edited audio |
| `packaging_staging` | `pending`, `reviewing`, `approved` | `jianying-packaging` | upper-track emphasis candidates have been reviewed |
| `packaging_apply` | `dry_run`, `applied`, `verified` | `jianying-editor` | the approved package was prepared, written, and independently read back |
| `visual_audio_review` | `pending`, `passed`, `needs_revision` | human/editorial review | the reopened Jianying result matches the intended visible and audible result |

`jianying-rough-cut` owns editorial decisions and plan status only. `jianying-editor` owns project probing, timeline reads/writes, cloning, and execution of approved ranges. A `content_pass` value or plan approval never by itself means that project execution occurred. If execution is required before a later stage, record an explicit `jianying-editor`-owned handoff/checkpoint confirming execution; without it, the later stage remains pending.

`human_review` is a flag on affected decisions or report rows, not a workflow state.

The normal gate is:

```text
content_pass stable/approved
→ subtitle_alignment approved
→ packaging_staging reviewing/approved
→ packaging_apply dry_run/applied/verified
→ visual_audio_review passed
```

If packaging discovers a semantic problem, set the packaging result to `needs_rough_cut_review` and return to the content owner. Do not silently consume the issue as a display-only change.

## Preparation coverage does not advance review state

The `run_fixed_workflow` / CLI `workflow` summary is coverage metadata, not a
claim of completed human review. `stage_count` and `provenance_counts` count
recorded deterministic stage reports, including failures. `waveform_passes`
counts the shared successful evidence stage once even when scans and subtitle
alignment reuse it; it is not a listening verdict or an FFmpeg-attempt count.

`agent_required_count` lists pending interpretation categories. `gate_counts`
counts declared human gate categories: three review gates and one listening
gate, all pending. A script-generated artifact never becomes `agent_interpreted`
or `human_verified` merely because the workflow succeeded. Record contextual
agent reasoning and human verdicts explicitly in the relevant report/plan;
agent playback or waveform analysis cannot satisfy `human_listening`.

Inspect `data.evidence_status` and `data.blocked_work` before handoff.
`unavailable_evidence_count` counts unavailable evidence categories;
`blocked_stage_count` counts distinct failed or skipped dependent stages, not
errors. Missing audio or unknown subtitle state blocks alignment; missing timed
transcript blocks generation and source-to-edited mapping; unresolved mapping
blocks candidate scans. Existing subtitles may still be aligned against edited
audio without a content mapping or transcript. This permitted partial path does
not establish that blocked content work passed. Out-of-scope transcript evidence
is `not_assessed`; missing required evidence remains `unavailable`.

When waveform extraction fails but a usable playback map permits text scans,
`candidate_scans` may succeed with `pause_scan_status=not_executed`. In this
partial result, `data.blocked_work` explicitly includes
`candidate_scans.pause_scan`, counted once in `blocked_stage_count`, alongside
blocked waveform extraction and subtitle alignment. Successful text-scan
reports and their candidates remain available; the aggregate candidate-stage
success does not imply that the audio-dependent pause scan ran.

Preparation does not set `content_pass` or `subtitle_alignment` to `stable` or
`approved`, clear `human_review`, or authorize a project write. Semantic
membership/order or protected-fact changes reopen rough-cut review and
`content_pass: draft`. See [scripted-workflow.md](scripted-workflow.md) for exact
counting units, pending categories, and partial-path behavior.

## Automation boundary

For the division between deterministic scripts, Agent interpretation, and
human approval, read [automation-boundary.md](automation-boundary.md).
Prioritize reducing repetitive search and candidate generation first; keep
semantic approval, protected-fact decisions, and listening gates human-owned.
