---
name: jianying-rough-cut
description: "Use when Chinese speech-led material needs editorial structure, delivery cleanup, transcript correction, or subtitle proofreading and alignment. Applies to interviews, tutorials, and lectures; does not write Jianying projects or authorize destructive edits from ASR alone."
---

# Jianying Speech-Led Editing

This is the content-intelligence and editorial-decision layer for Jianying speech-led editing. It runs a two-stage flow: **content rough cut** decides *what the audience should hear* (structure, keep/drop, order), and **delivery refinement** improves *how it is delivered* (fillers, pauses, repetition, tone, hard joins) and aligns subtitles. Both stages protect technical meaning and continuity and emit an auditable plan. The subtitle workflow supports current-subtitle alignment and no-subtitle generation, but the skill only consumes application-independent evidence: it never reads or writes a Jianying draft or calls `jianying-editor`.

## Positioning

- **Owns:** source completeness and orientation, the transcript correction gate (fix misheard text before deciding), semantic segmentation, speaker and Q&A structure, and protected facts; **content rough cut** (keep/drop/order decisions at block level, via the copy-first or discovery entry); **delivery refinement** (the main loop for fillers, false starts, repeated openings, stutters, redundant restatements, excess pauses, hard joins, and subtitle proofreading/alignment after the edited timeline is saved); and the Pass 3 retrospective that turns human corrections into dictionary, preference, and case-law learning.
- **Produces:** an application-independent content decision plan, a copy-first material index (numbered source clips mapped to script segments, with the surviving take chosen) when the speaker worked from a written copy, a generated speaker-labelled transcript as the analysis substrate for interview / no-copy material, a transcript correction table plus unresolved-term list, a repeated-attempt rollup, tiered verification labels, a separate subtitle-alignment plan when that stage is requested, and a Pass 3 learning record.
- **Handoff:** an external, explicitly approved handoff may let `jianying-editor` resolve approved ranges against the current saved draft; `jianying-packaging` starts only after content and subtitle alignment are stable or approved.
- **Does not own:** direct Jianying project writes, flower text, upper-track styling, templates, transitions, overlays, sound effects, or non-speech montage editing. Non-goal: this layer borrows editorial *method* only and never re-implements a proprietary editing runtime (a persistent service, a workbench/Studio UI, a revision-compare-and-swap ledger, forced cloud-only ASR, or a word-id cut store). Project state, probing, and every write belong to `jianying-editor`; this skill only emits validated, application-independent plans.

“Intelligent” means evidence-backed semantic judgment with reviewable uncertainty—not blind deletion based on transcript text, punctuation, or pause length.

The surrounding workflow may be `jianying-rough-cut → (explicit handoff) jianying-editor → jianying-packaging`. This editing skill itself does not probe a saved draft, resolve encrypted project state, or apply a plan. Use [references/workflow-state.md](references/workflow-state.md) for the shared handoff states.

Project-specific conventions must be supplied through an external project case reference. This reusable Skill does not bundle a user's copy, timing, track, or style decisions.

## Flow Control

One `content_edit` run is a two-stage pipeline with human gates. A blocked condition stops forward motion; a semantic finding from the packaging stage loops back to the content rough cut. Schema phase keys are unchanged: content rough cut → `workflow.content_pass`, delivery refinement → `workflow.refinement_pass`.

```text
[Entry] Written copy?  ──yes──▶ Content rough cut · Copy-first   (references/copy-first-rough-cut.md)
                      └─no──▶ Content rough cut · Discovery     (references/discovery-rough-cut.md: transcription + speaker labels → outline → scope consultation → plan)
   │  Produce a content decision plan; set workflow.content_pass = draft
   ▼
[Gate] Is content_pass stable or approved?  no → continue the content rough cut
   │  Block high-confidence destructive decisions when audio is missing, subtitle state is unknown, the transcript correction gate is incomplete, or the domain or terminology is unresolved.
   ▼  yes
[Delivery-refinement loop · may repeat]  Pass 2 cleanup (repetition / pauses / breaths / fillers / unnatural delivery) → subtitle alignment → SRT; set workflow.refinement_pass
   ▼
[Execution handoff] After explicit confirmation, `jianying-editor` applies approved ranges to the timeline and aligns subtitles.
   │  If a range cannot be resolved, a cut lands mid-phrase, or order or audio/video sync drifts, report the affected segment; do not silently move boundaries or retime it.
   ▼
[Review] Human review: content_pass → subtitle_alignment → visual_audio_review (references/workflow-state.md)
   ▼
[Exit] Passed → ask whether to continue to jianying-packaging (emphasis text / highlights / transitions / sound effects)
   ▲                                   │
   └───────── needs_rough_cut_review ──┘  If packaging finds a semantic issue, return to the content rough cut; do not hide it as a display-layer change.
```

Standing rules that drive the arrows: complete the content rough cut before delivery refinement — never refine while `content_pass` is `draft`; re-audition every refinement candidate in context and use waveform evidence as the boundary authority; this skill emits validated plans only, and every draft read/write belongs to the `jianying-editor` handoff. `subtitle_alignment` mode enters at the delivery-refinement subtitle step; `final_draft_audit` is read-only and cuts nothing.

## Timeline naming on creation or cloning

Whenever this workflow creates a fresh timeline or clones a source into a working copy (including the rough-cut copy applied through the `jianying-editor` handoff), name it `<源名>·<用途>·<时间戳>`:

- `源名`: the source timeline's base name, kept verbatim including any leading serial number (e.g. `01智能`), so downstream batch matching by序号 still resolves. Never strip or renumber it here.
- `用途`: a single purpose token for the new timeline — `粗剪` (rough-cut/edit copy), `重点句` (emphasis/flower-text clone), `包装` (final packaging clone), or `音效` (sound-only pass). A genuinely new purpose gets its own token; do not overload an existing one.
- `时间戳`: creation time as compact `MMDD-HHMM` in the operator's local zone (e.g. Asia/Shanghai). Two clones sharing the same `源名`+`用途` in one session are told apart by this token, never by an appended `(2)`.

Concrete `源名` strings, copy, and serial numbers stay in the external project case reference; only this `<源名>·<用途>·<时间戳>` format is reusable guidance.

## Operating modes

Use one explicit mode for each request:

- `content_edit`: run the full two-stage edit — **content rough cut** (structure via the copy-first or discovery entry) then **delivery refinement** (the refinement main loop) — and produce an auditable content decision plan and, on request, a subtitle-alignment plan. This is the default mode.
- `subtitle_alignment`: the **delivery-refinement** subtitle step alone — align an existing subtitle list or generate review-pending subtitles from a timed transcript against edited-timeline audio. Do not make content rough-cut decisions, probe a Jianying draft, or write a project.
- `final_draft_audit`: inspect an already saved final or near-final timeline without proposing edits. The current rendered/visible final subtitle is the report's wording authority; ASR, old subtitles, and internal fields are evidence for discrepancies only.

In `subtitle_alignment`, establish application-independent audio and subtitle-state evidence, then use the subtitle route in [references/subtitle-proofreading-and-audio-alignment.md](references/subtitle-proofreading-and-audio-alignment.md). Do not force a full content-orientation or refinement pass unless the user also requested content editing.

In `final_draft_audit`:

- do not silently replace final subtitle wording with ASR wording;
- mark subtitle/audio disagreements, old-wording remnants, and uncertain technical terms as `human_review`;
- report semantic groups, ordering, packaging mismatches, and evidence only;
- do not emit delete, shorten, reorder, join, or write-back instructions;
- validate the report with `python scripts/roughcut_tool.py validate report <report.json>`.

Use [references/analysis-report-schema.md](references/analysis-report-schema.md) for the report contract.

When comparing multiple timelines, read [references/timeline-comparison.md](references/timeline-comparison.md). A changed order or duration invalidates direct reuse of old timecodes; remap by semantic-unit ID and context before handing evidence to packaging.

## Governing priority

Semantic correctness > content completeness > logical continuity > information density > rhythm > absolute duration.

Never shorten a piece by changing the speaker's meaning. Protect numbers, units, conditions, causes, prerequisites, negations, comparisons, names, technical terms, and uncertainty qualifiers.

## Evidence

Use any available combination of video, audio, waveform, ASR transcript, subtitles, time-coded transcript, speaker labels, and an already edited version. Do not require video when audio and time-coded speech are sufficient.

Treat ASR, punctuation, and diarization as evidence rather than truth. When audio is available, use it to resolve boundaries, fillers, pauses, overlap, tone, and suspicious transcript text. Record which evidence supports each decision.

Before making destructive decisions, audit material completeness. Record whether the available video, audio, transcript/ASR, subtitle timing, and other evidence are complete, partial, or unknown; list what was checked, what is missing, the evidence for the assessment, and whether the limitation requires review. A missing source must not be silently treated as an empty section.

Tag every reported conclusion with a verification tier (`plan_consistency` / `visual_frame` / `human_listening`) at the weakest level its evidence supports, and never promote a transcript, waveform, DOM, or media-probe result into a listening or visual verdict. See [references/verification-levels.md](references/verification-levels.md).

## Mandatory workflow

For `content_edit`, the following order is required. Do not propose definite deletion, shortening, deduplication, or reordering before the correction gate and the orientation and outline stages are complete. For `subtitle_alignment`, skip the content-cut stages and begin at the subtitle stage after the input-state audit.

**The content rough cut has two entries that share one delivery-refinement tail.** Pick the entry based on whether the speaker had a written script:

- **Content rough cut · Copy-first** — the speaker recorded to a written script. The copy is the structural spine; the front end is a numbered material index, whole-clip take selection, and ordering the kept units by the copy while dropping re-takes, countdown lead-ins, and off-copy digressions. Follow [references/copy-first-rough-cut.md](references/copy-first-rough-cut.md).
- **Content rough cut · Discovery** — interviews, conversations, talk shows, or any material without an accurate copy. There is nothing to order against, so the front end transcribes and diarizes first, builds the outline from the transcript, agrees scope and order with the human, then plans the block-level rough cut (coarse pass first). Follow [references/discovery-rough-cut.md](references/discovery-rough-cut.md).

Only each entry's **front end (content rough cut)** differs. The **delivery-refinement** tail — the refinement main loop, subtitle/SRT, and the `jianying-editor` handoff — is shared (steps 11–13 below; steps 14–15 are the post-review retrospective and stage-diff, which edit nothing). Neither entry changes the plan schema, probes a draft, or writes to a draft.

1. Establish the requested outcome, target audience, platform/pace, duration constraint, and preservation requirements when they affect decisions. When there is no accurate copy, make this an explicit one-time scope-and-order consultation before the outline locks (see the discovery runbook): recommend what to keep or drop at block level and whether to preserve chronological order, then take direction — a single brief, never a per-cut confirmation.
2. Read or listen through the complete available material, perform the material-completeness audit, and record evidence sources and limitations.
3. Run the transcript correction gate in [references/transcript-correction-gate.md](references/transcript-correction-gate.md): correct misheard text against the general and per-user dictionaries (plus a one-time script alignment only when the dictionary cannot settle a term and the speaker's own script exists), and produce the applied-corrections table plus unresolved list before any cut decision. A misheard name is not a deletion reason; fix text first.
4. Complete the content-orientation stage in [references/domain-and-outline.md](references/domain-and-outline.md): identify the theme, thesis, purpose, audience, professional domain, terminology, entities, protected facts, and information outline.
5. If the domain or a technical term is uncertain, mark the affected units for context or human review. For high-stakes domains, verify against authoritative references when appropriate; otherwise do not make a definite destructive decision.
6. Reconstruct complete semantic units across transcript segments. ASR rows and subtitle cues are timing containers, not sentence or idea boundaries.
7. Identify stable speakers and per-unit conversational functions such as host, questioner, respondent, expert, narrator, correction, or supplement. For multi-speaker/Q&A work, read [references/dialogue-and-qa.md](references/dialogue-and-qa.md).
8. Build the original content map before proposing deletions. For detailed criteria, read [references/content-analysis.md](references/content-analysis.md).
9. **Content rough cut:** Produce the first-pass content rough cut. Preserve complete meaning and allow natural breaths, modest pauses, and harmless small repetitions.
10. Audit the proposed cut against the complete source for missing context, altered claims, incorrect question/answer pairing, out-of-order logic, technical-detail loss, and domain terminology loss.
11. **Delivery refinement:** Mark the content pass as draft, stable, or approved. Only when it is stable or approved, produce a separate refinement pass for fillers, false starts, repeated openings, stutters, redundant restatements, excess pauses, tiny audio remnants, and hard joins. Run it as five single-criterion scans (one criterion per read) in [references/speech-cleanup.md](references/speech-cleanup.md), apply the case-law in [references/cut-case-law.md](references/cut-case-law.md), and honor the boundary rules in [references/audio-boundaries.md](references/audio-boundaries.md). This refinement is iterative and may loop: re-run the scans and re-audition in context until the delivery reads naturally, revisiting any unit that still misfires.
12. Output the independent content decision plan described in [references/decision-plan-schema.md](references/decision-plan-schema.md). Do not output an application-specific execution handoff.
13. **Delivery refinement:** After the content pass has been executed, or directly for `subtitle_alignment`, run the subtitle proofreading and audio-alignment stage in [references/subtitle-proofreading-and-audio-alignment.md](references/subtitle-proofreading-and-audio-alignment.md). For an existing subtitle list, use `python scripts/roughcut_tool.py subtitle-align --audio <edited-audio> --subtitles <current-subtitles> --out <plan.json>`; for a timeline with no subtitles, use `python scripts/roughcut_tool.py subtitle-generate --audio <edited-audio> --transcript <timed-transcript> --out <plan.json> [--srt-out <preview.srt>]`. Both paths require edited-timeline audio or precomputed waveform evidence; unreadable subtitle state and missing audio block before waveform analysis. The generated path requires timed `segment`/`word` evidence and keeps `review_status=pending`. In both paths waveform evidence is the boundary authority; `build-alignment` remains a token-map arithmetic helper and cannot by itself prove alignment. Validate the separate [references/alignment-plan.md](references/alignment-plan.md) contract with `python scripts/roughcut_tool.py validate alignment <plan.json>`. The review-pending SRT may be saved beside the media (for example, in the draft folder) as a sidecar; it remains a review artifact, never a write-back source, and saving a plain file there is not a draft write. Hand off only after human listening and approval; if that handoff would involve `jianying-editor`, ask for explicit confirmation first. When approved ranges are later resolved against the saved draft — importing clips and aligning cut segments — report an unresolved range, a cut landing mid-word, or order/sync drift for the affected segment with evidence; never silently nudge or retime it inside this skill.
14. After the human reviews the result, run the Pass 3 retrospective in [references/preference-and-dictionary.md](references/preference-and-dictionary.md): diff the approved proposal against the final plan, and archive taste differences to the preference file, corrected proper nouns to the dictionary, and rule gaps to the pending-cases drawer. This stage records learning only; it never mutates a draft.
15. When comparing completed stages, run `python scripts/roughcut_tool.py stage-diff --source <source.json> --target <target.json>`. Record display-only text changes separately from semantic/subtitle changes, and annotate excluded compound intervals without opening them.

## Content orientation gate

The orientation report must contain, at minimum:

- a theme and one-sentence thesis with confidence;
- the purpose and audience assumption;
- a primary domain or an explicit uncertain/non-specialized classification;
- domain segments when the material covers more than one field;
- terminology, acronyms, named entities, numbers, units, parameters, ranges, and conditions;
- possible ASR errors and unresolved terms;
- an outline of topics, questions, answers, explanations, examples, evidence, qualifications, conclusions, CTA, digressions, and low-information units;
- protected facts and dependencies that must survive editing.

If the orientation is incomplete, the output may contain hypotheses and review candidates, but it must not contain high-confidence destructive decisions for affected material.

## Content Rough Cut and Delivery Refinement: Two-Pass Boundary

### Pass 1: Content Rough Cut

Optimize correctness, structure, and completeness. Remove clear digressions, failed takes fully covered by a complete take, large redundant passages, and content outside the agreed scope. Keep uncertain material for review.

This pass may retain natural breaths, short thinking pauses, contextual discourse markers, and small repetitions that do not impair understanding.

### Pass 2: Delivery Refinement

After Pass 1 is approved or stable, tighten delivery at phrase and audio-boundary level. Prefer small local cuts over deleting whole sentences. Preserve one natural connector when repeated openings are reduced. Compress pauses rather than forcing speech to zero gap.

Every refinement candidate must be re-auditioned in context. A clean transcript does not prove a natural audio join.

The plan must record the phase status separately: `workflow.content_pass` is `draft`, `stable`, or `approved`; `workflow.refinement_pass` is `not_started`, `draft`, or `approved`. Refinement decisions are not valid while the content pass is still draft.

### Pass 3: retrospective (learning only)

Passes 1 (content rough cut) and 2 (delivery refinement) are the only cutting passes; Pass 3 does not edit content. After the human reviews an executed result, run the retrospective in [references/preference-and-dictionary.md](references/preference-and-dictionary.md): diff the approved proposal against the final plan and persist restored cuts, missed cuts, and the dictionary/preference/pending-case updates they imply. It is gated by `content_pass` being `stable` or `approved` and never mutates a draft or a shipped plan.

## Decision rules

- Edit complete semantic units unless the defect is a local filler, false start, stutter, or pause.
- Do not stitch unfinished fragments from different attempts into a synthetic statement. A later take is not automatically better; keep the complete, natural, accurate, contextually connected version.
- Repetition, discourse markers, and overlap: remove only when no new premise, emphasis, emotion, contrast, clarification, condition, or speaker contribution is lost. Criteria in [references/speech-cleanup.md](references/speech-cleanup.md) and [references/dialogue-and-qa.md](references/dialogue-and-qa.md).
- Reordering moves complete semantic units. Recheck pronouns, connectors, chronology, causal dependencies, and domain conditions afterward.
- Record start/end boundary basis for every decision. Exact timestamps when evidence permits; approximate boundary on a destructive action must remain reviewable and may not be high-confidence.
- A cut decision is binary: commit it as `delete`/`shorten`/`reorder`/`join` after self-verification, mark it `review`, or drop it. Do not emit a "suggest deleting, awaiting the user" third state or ask line by line. Risk changes only how hard you verify, not the shape of the output. If you cannot confirm after re-reading in context, leave the unit out; when uncertain, do not list it for deletion. A `review` decision keeps the unit in place pending a listening/context judgment about whether it belongs; it is never a committed deletion waiting for a nod.
- Boundary evidence and picture-lock rules: [references/audio-boundaries.md](references/audio-boundaries.md) and [references/content-analysis.md](references/content-analysis.md). Do not infer frame-accurate boundaries from vague instructions alone. Picture-lock only where a shot boundary carries a real semantic constraint.
- Time thresholds may flag pause candidates but may not authorize deletion by themselves.
- When evidence is insufficient, use `needs_listen`, `needs_context`, `low_confidence`, or `human_review`; do not convert uncertainty into a delete instruction.
- Before presenting the plan, re-read the post-cut text in playback order and revoke any line that no longer reads through. Self-verification means you re-reading it against the audio and context, not forwarding the decision to the user. A clean transcript never proves a natural join.
- When material is partial or unknown, do not mark an affected delete, shorten, reorder, or join as high-confidence. Add a review flag to lower-confidence candidates.
- When a decision touches a domain-sensitive fact, terminology, number, unit, condition, or entity, record that sensitivity and retain the evidence.
- Subtitle recognition text is evidence, not truth. Correct current saved subtitles against edited-timeline audio before packaging; do not use an older subtitle copy as the write source.
- In `existing`, current visible subtitle text, order, and segmentation are authoritative; ASR is cross-check evidence only. In `generate`, require timed transcript evidence, apply dictionary corrections to text only, and never alter token or semantic-unit timestamps during correction.
- Record `audio`, `picture`, or `manual` mode plus boundary basis, evidence, confidence, and review state for both ends of every aligned subtitle unit (see [references/alignment-plan.md](references/alignment-plan.md)).
- When the workflow mode is `final_draft_audit`, declare `final_visible_subtitle` as the text authority and keep all ASR/final-text differences reviewable; do not turn them into corrections inside this skill.
- Waveform thresholds locate candidates; they never authorize deletion or splitting by themselves. Word-level timestamps are cross-check evidence and require a health check.

## Script-first execution

Use [references/scripted-workflow.md](references/scripted-workflow.md) as the
fixed routing table. The `workflow` command accepts `subtitle_mode=auto`,
`existing`, or `generate`; it runs deterministic preparation in one process and
reuses one waveform pass for pause scanning and subtitle alignment. `auto` is
fail-closed when subtitle state is missing or ambiguous. The human still owns
semantic orientation, unresolved technical terms, contextual listening, edge
approval, and plan approval. This skill does not call `jianying-editor`, read a
Jianying project, or write back a draft.

## Required outputs

`content_edit` produces the full content-analysis outputs below. `subtitle_alignment` produces the input/state evidence, a separate pending `subtitle_alignment_plan`, and an optional UTF-8 SRT review artifact; it does not need to fabricate content-orientation or cut-decision fields.

- source/evidence summary and limitations;
- material-completeness status, checked sources, missing items, supporting evidence, and review impact;
- transcript correction table (applied `original → corrected → context`) and the unresolved-term list that must not be guessed;
- theme, thesis, purpose, audience, and confidence;
- domain analysis, terminology, entities, protected facts, and confidence;
- original information outline with time ranges, roles, dependencies, and confidence;
- speaker/role map with confidence;
- recommended content structure;
- Pass 1 decision table;
- Pass 2 refinement candidates kept separate from Pass 1;
- repeated-attempt rollup (idea recorded more than once: times said, take kept, takes removed, risk);
- each conclusion tagged with its verification tier (`plan_consistency` / `visual_frame` / `human_listening`) and never upgraded beyond its evidence;
- after human review, the Pass 3 learning record: restored cuts, missed cuts, and the dictionary/preference/pending-case updates they produced;
- a generic `learning_report` with evidence level, generalizability, anti-pattern, promotion status, and an optional external `case_ref`;
- a stage-diff report with order fingerprints, semantic mapping, text-authority changes, packaging additions, and compound-exclusion annotations;
- sequence, speaker, overlap, and continuity issues;
- semantic highlight groups using the shared roles `hook`, `background`, `question`, `reaction`, `answer`, `evidence`, `technical_detail`, `contrast`, `benefit`, `summary`, and `cta`;
- for each highlight group: semantic-unit references, context dependency, speaker/function, short-video value, protected-fact flags, and whether human listening is required;
- in `final_draft_audit`, a read-only analysis report with final-subtitle authority and discrepancy review state;
- protected facts and risk points;
- estimated duration change when timing evidence permits;
- expected join description for every removal or reorder;
- start/end boundary basis, evidence, and precision for every decision;
- an independent content decision plan with no application-specific execution fields.
- a separate application-independent `subtitle_alignment_plan` with corrected text, semantic unit IDs, audio/picture/manual boundary decisions, evidence, and re-alignment triggers.

Run `python scripts/roughcut_tool.py validate plan <plan.json>` to validate the content decision plan before presenting it for review.

## Tool layer

`scripts/roughcut_tool.py` is the application-independent rough-cut CLI. Its importable functions live under `scripts/roughcut_tools/`; they audit material completeness, apply confirmed dictionary corrections, map source tokens into playback time, produce conservative cleanup candidates, extract waveform evidence, build waveform-first subtitle-alignment candidates, generate timed-transcript subtitle units and UTF-8 SRT previews, compare semantic order, produce multi-stage `stage-diff` reports, emit external-case `learning_report` records, run the fixed preparation workflow, and generate retrospective reports. It never writes a Jianying draft, never reruns ASR for subtitle timing, and never converts a candidate into an automatic delete. For high-precision subtitle work, waveform evidence is the boundary authority; ASR word timing is cross-check evidence for existing subtitles and required input evidence (but not boundary authority) for generation.

The CLI returns a JSON report envelope by default (`data`, `errors`, `input_errors`, `warnings`, and status fields), accepts a previous complete report or raw data JSON, and supports `--format text` for humans. Exit code `0` is a usable report including review warnings, `1` is an evidence/validation/safety block, and `2` is a malformed JSON, missing/unreadable file, argument, or output-path error. A playback map is fail-closed: every token is kept, explicitly deleted, or reported unresolved; scans require canonical `units`; pause scans require audio or precomputed pause evidence. Candidate scans emit only `review`/`needs_listen` evidence and never automatic delete instructions.
