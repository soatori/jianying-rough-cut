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

The normal review-state progression is:

```text
content_pass stable/approved
→ subtitle_alignment approved
→ packaging_staging reviewing/approved
→ packaging_apply dry_run/applied/verified
→ visual_audio_review passed
```

The diagram describes state progression. A write still has to satisfy the
phase-specific approval and authorization gates below.

## Packaging phase gates

Use these gates consistently across `jianying-rough-cut`, `jianying-packaging`,
and the `jianying-editor` handoff:

| Operation | Required state | Write authorization | Next-step suggestion |
|---|---|---|---|
| Read-only analysis | Any state; report the current state and unresolved evidence | None; analysis must not create a clone or staging layer | Deliver the report and stop; continue only if the user requests another mode. |
| Prepare a packaging plan | `content_pass: stable` or `approved`; `subtitle_alignment: approved` | No draft write | Validate and deliver the plan; prepare staging only when requested and its stricter gate passes. |
| Create or update a staging timeline | `content_pass: approved`; `subtitle_alignment: approved` | The request must authorize staging for the current source and scope; use a fresh clone when no target is specified | Set `packaging_staging: reviewing`, identify the copy to open, and wait for the user's review. |
| Apply the final package | `content_pass: approved`; `subtitle_alignment: approved`; `packaging_staging: approved`; approved final-subtitle reference; remapping `verified` or `not_required` | The request must authorize final application to the approved staging target | Read back the editor result, then reopen Jianying for visual/audio review. |

`stable` means the rough-cut owner has completed a semantic self-audit; it does
not mean the user approved the content. A structurally valid review plan may
record `stable`, but it must not be handed to `jianying-editor` for a staging or
final write until the write gate above is met. Plan approval alone does not
authorize a draft mutation. An explicit request to perform a specific write is
authorization for that unchanged scope; do not ask the user to authorize it a
second time. Use a fresh clone when no target is specified. Ask only when the
source, scope, explicit target constraint, or authorization is ambiguous,
missing, or has changed. Re-read and compare the saved source and target before
each write.

If packaging discovers a semantic problem, set the packaging result to `needs_rough_cut_review` and return to the content owner. Do not silently consume the issue as a display-only change.

## Preparation coverage does not advance review state

The `run_fixed_workflow` / CLI `workflow` summary is coverage metadata, not a
claim of completed human review. The CLI requires `content`, `delivery`,
`subtitle_alignment`, or `all`; it never defaults to a full run. `stage_count`
and `provenance_counts` count attempted deterministic stages, including
failures. `executed_stages` keeps failed attempts visible. `skipped_stages`
marks out-of-scope work as `not_requested` and selected work that did not run as
`blocked` or `not_applicable`. Only selected-scope work appears in
`blocked_work`.

`waveform_passes` counts the shared successful evidence stage once when a
selected scope uses it; in `all`, scans and subtitle alignment reuse the same
result. It is not a listening verdict or an FFmpeg-attempt count.
`agent_required` and `review_gates` contain only the selected scope's pending
categories. A script-generated artifact never becomes `agent_interpreted` or
`human_verified` merely because the workflow succeeded. Record contextual agent
reasoning and human verdicts explicitly in the relevant report/plan; agent
playback or waveform analysis cannot satisfy `human_listening`.

Inspect `data.evidence_status`, `executed_stages`, `skipped_stages`, and
`blocked_work` before handoff. Out-of-scope evidence is `not_assessed`;
`unavailable_evidence_count` counts only unavailable evidence categories.
Missing audio or unknown subtitle state blocks selected alignment work; missing
timed transcript blocks selected generation or source-to-edited mapping;
unresolved mapping blocks selected candidate scans. Existing subtitles may be
aligned against edited audio without a content mapping or transcript.
In `all`, a blocked subtitle branch does not stop independent delivery stages
when their own audio and playback evidence is available.

When waveform extraction fails but a usable playback map permits text scans,
`candidate_scans` may succeed with `pause_scan_status=not_executed`. The
selected-scope `blocked_work` includes `candidate_scans.pause_scan`; in `all`,
it also includes blocked waveform extraction and subtitle alignment. Successful
text-scan reports and candidates remain available, but aggregate scan success
does not imply that the audio-dependent pause scan ran.

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
