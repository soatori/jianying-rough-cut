# Script-first rough-cut workflow

Use the CLI for deterministic preparation. Keep semantic judgment, technical
listening, and approval as explicit human gates.

"Script-first" means *CLI-script-first* deterministic prep, unrelated to whether
the speaker had a written 文案 — the 文案 / 无文案 choice lives in the copy-first
and discovery runbooks.

`workflow` requires an explicit scope in the bundle or on the CLI. The CLI
`--scope` overrides the bundle. Missing or invalid scope returns
`scope_required` or `invalid_scope`; the command never defaults to a full run.

| Scope | Runs | Excludes |
|---|---|---|
| `content` | material audit, transcript correction, playback-map preparation | waveform, candidate scans, subtitle alignment |
| `delivery` | candidate scans and the waveform evidence they need | material audit, transcript correction, playback-map building, subtitle alignment |
| `subtitle_alignment` | existing or generated subtitle path and one waveform pass | material audit, candidate scans, edit-map/playback-map work |
| `all` | the full chain, sharing one waveform result between pause scans and alignment | — |

`candidate_scans` means delivery-cleanup scans for fillers, repetitions,
false starts, retakes, or pauses. Subtitle alignment emits separate
review-pending boundary candidates; its scope does not run delivery
`candidate_scans`.

`subtitle_mode` (`auto`, `existing`, or `generate`) only affects
`subtitle_alignment` and `all`. `auto` chooses an existing-subtitle or
generation path; it never chooses the workflow scope. Existing-subtitle-only
alignment may proceed without a transcript. Playback-map creation and subtitle
generation require timed transcript evidence. If it is missing, block only the
dependent stage and request the transcript or authorized transcription.

For subtitle alignment, the input must identify audio from final edited
playback order (or precomputed waveform evidence), including its duration and
preferably a content hash. Missing, stale, source-only, or unreadable audio
blocks before generation and FFmpeg; request a fresh application-independent
mixdown rather than infer project clip selection inside this skill.

## Two subtitle modes

The subtitle path has two explicit modes. `existing` treats the current visible
subtitle units as authoritative for wording, order, and segmentation; waveform
analysis only supplies boundary candidates and review evidence. `generate` is
used only when the timeline has no subtitles and a timed transcript is
available. It corrects text, keeps the transcript's token/segment times, then
uses the edited-timeline waveform to build a review-pending alignment plan.

`auto` is fail-closed within a requested subtitle scope: a non-empty `subtitles` input selects `existing`; an
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
source. `validate alignment <plan>` checks the plan structure and its recorded
identity only; it does not reread audio. If audio changes, rerun `subtitle-align`
or `workflow --scope subtitle_alignment` to produce fresh evidence. Identical
adjacent subtitle text produces a warning unless the unit carries intentional
repeat evidence. The command does not restore an older script order, overwrite wording,
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

Place the application-independent inputs for the requested work in one
`workflow` bundle. The bundle must include its scope; the CLI flag may override
it. For example, to run the full chain:

```powershell
python scripts/roughcut_tool.py workflow \
  --input "<roughcut-workflow.json>" \
  --scope all \
  --format text \
  --out "<roughcut-workflow-report.json>"
```

Build the bundle once for the requested scope and invoke `workflow` once. Do not
rerun stages listed as successful in `executed_stages` while their inputs are
unchanged. If a stage is blocked, correct its missing or invalid input before
rerunning the requested scope. Use `--format text --out <report.json>` for
Agent runs: the CLI prints a compact summary and stores the full JSON report at
the specified path. Pass the report path and only the required artifact paths
to the next phase instead of copying the full report into the conversation.

Reuse supplied playback maps and precomputed waveform evidence while their
recorded source identities and input files remain unchanged. Refresh waveform
evidence when the edited audio hash or duration changes; rebuild the affected
bundle when its transcript, subtitle state, edit map, playback order, or
selected scope changes. Never infer current evidence from a report for an older
input state.

For a scope-specific run, replace `all` with `content`, `delivery`, or
`subtitle_alignment`. `--subtitle-mode` overrides only the subtitle path and
has no effect for `content` or `delivery`. Add `--srt-out
"<subtitle-preview.srt>"` only when the scope produces a subtitle alignment
plan.

Use a standalone CLI command only when it fully represents the requested
single-stage task. Do not run both a standalone command and `workflow` for the
same unchanged inputs.

The bundle must contain `scope` and may contain `inputs`, `transcript`,
`edit_map`, `playback_map`, `subtitles`, `audio`, `dictionaries`, `preferences`,
`pause_config`, and `subtitle_mode`. `audio` may be the edited-audio path or a
precomputed waveform-evidence JSON accepted by the waveform loader. For
`subtitle_mode=existing`, `subtitles` must be non-empty. For
`subtitle_mode=generate`, `subtitles` must be absent or explicitly empty and
`transcript` must contain timed segments or words. With `subtitle_mode=auto`,
use a non-empty subtitle list for the existing path or an explicit empty list
plus timed transcript for the generation path; otherwise the workflow blocks
because the subtitle state is unknown.

`all` reuses the single waveform result for pause scanning and subtitle
alignment. `executed_stages` lists attempted stages, including failed ones;
`skipped_stages` marks out-of-scope stages as `not_requested` and selected but
unrun stages as `blocked` or `not_applicable`. A failed stage remains in
`executed_stages` and appears in `blocked_work`. `blocked_work` contains only
selected-scope work. This workflow never invokes `jianying-editor`, reads a
Jianying project, or writes a Jianying draft.

## Coverage summary and pending work

The `workflow` summary is coverage metadata, not completed semantic work or
completed human review. Its counts describe this preparation run only:

| Field | Counting unit and limit |
|---|---|
| `scope` | The one selected workflow scope. |
| `stage_count` | Recorded deterministic stage reports, including failed attempts; skipped stages are excluded. |
| `executed_stages` | Stage names attempted during this run; failures remain listed. |
| `skipped_stages` | Stage-name to reason mapping: `not_requested`, `blocked`, or `not_applicable`. |
| `artifact_count` | Artifact entries emitted by stages; inspect stage status before consuming them. |
| `waveform_passes` | Successful shared waveform-evidence stage: zero or one. Precomputed evidence counts once; scans and alignment reuse it. This is not the number of FFmpeg calls, normalizations, or failed attempts. |
| `provenance_counts` | Top-level stage reports by `script_generated`, `agent_interpreted`, `human_verified`, or `unavailable`. Each stage explicitly labels its deterministic preparation as `script_generated`, including failed reports; this does not relabel its input evidence or mean its contents were reviewed. Agent/human counts remain zero. |
| `agent_required_count` | Scope-specific follow-up categories in `data.agent_required`; these are requirements, not completed actions or per-candidate counts. |
| `gate_counts` | Scope-specific human gates in `data.review_gates`; all remain pending until explicitly reviewed. Counts are gate categories, not reviewed rows or listened-to edges. |
| `blocked_stage_count` | Unique selected-scope names in `data.blocked_work`: failed stages plus work not run because a prerequisite was unavailable. Out-of-scope stages are excluded. |
| `unavailable_evidence_count` | Unavailable entries in `data.evidence_status`, counted once per evidence category rather than per error or affected stage. |

`data.evidence_status` distinguishes audio, transcript, subtitle state, and
playback mapping. Out-of-scope evidence is `not_assessed`. `available` means readable/accepted at the relevant
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
continue. Inspect `executed_stages`, `skipped_stages`, and `blocked_work` before
handoff. Early returns retain the same coverage fields, and no evidence count
clears a gate.

Agent interpretation must supply contextual reasoning and provenance separately.
Neither ASR, a long pause, a waveform edge, nor a successful CLI run authorizes
deleting, splitting, joining, or removing a pause. Semantic membership/order or
protected-fact changes return to rough-cut review. A recorded human verdict is
required to clear `human_listening`; agent playback cannot clear it. This
workflow does not ingest verdicts or advance review states automatically.

This skill never probes, resolves, clones, or writes a Jianying draft. When the
requested work needs draft evidence or a project mutation, hand it to
`jianying-editor` only when that operation is within the user's current request
and authorization. Otherwise request the missing evidence or authorization.
Approval of a plan alone does not authorize a project write. Do not ask again
for an already authorized operation while its scope and target remain
unchanged.
