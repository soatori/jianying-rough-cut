---
name: jianying-rough-cut
description: "Use when Chinese speech-led material needs editorial structure, delivery cleanup, transcript correction, subtitle proofreading/alignment, or read-only comparison of source, rough cut, intermediate edit stage, manual fine cut, and reference stages to detect content loss or boundary changes. Does not write Jianying projects or authorize destructive edits from ASR alone."
---

# Jianying Speech-Led Editing

Use this skill to plan speech-led content edits and subtitle alignment from source evidence. It emits application-independent, reviewable plans; it never reads or writes a Jianying draft.

## Scope and handoff

- Owns transcript correction, source completeness, content structure, speaker/Q&A relationships, speech cleanup, subtitle proofreading/alignment plans, comparison review, and post-review learning.
- jianying-editor owns project probing, timeline reads/writes, cloning, and execution of approved ranges. This skill does not create, clone, or name timelines.
- jianying-packaging owns visual emphasis, flower text, motion, transitions, overlays, and sound effects. It starts after content and subtitle alignment are stable or approved.
- Keep project-specific copy, names, timings, IDs, assets, and manual choices in external case references, not in this reusable skill.

## Modes

- **content_edit** (default): plan the content rough cut, then delivery refinement, then subtitle alignment as requested.
- **stage_comparison:** collect and compare supplied edit stages read-only; route source-plus-subtitle-only work to **subtitle_alignment**.
- **subtitle_alignment:** proofread or generate review-pending subtitles against edited audio; do not make content-cut decisions.
- **final_draft_audit:** read-only discrepancy report. The current rendered/visible subtitle is the wording authority; do not propose cuts or write-back instructions.

## Core workflow

For **content_edit**, choose the entry by source evidence:

1. Use **copy-first** only when an accurate written script is available and the speaker recorded to it. Otherwise use **discovery** for interviews, conversations, or unscripted material. Read the applicable entry reference below.
2. Audit source completeness and limitations. Correct confirmed transcript errors and record unresolved terms before making cut decisions.
3. Orient to the whole source: identify its thesis, audience, domain, speakers, outline, dependencies, and protected facts.
4. Produce the content rough-cut plan from complete semantic units. Audit it against the full source for missing context, altered claims, broken Q&A, lost technical conditions, and logic/order problems.
5. Record `content_pass: draft` after evidence collection. Set it to `stable` only after the semantic self-audit, and to `approved` only after explicit user approval.
6. Once stable or approved, refine delivery: review fillers, false starts, repetitions, pauses, and joins in context. Audition every proposed change when audio access is available; otherwise keep `human_listening` pending.
7. Proofread current subtitles or generate a separate pending alignment plan from a timed transcript. After human review, record learning and stage differences without changing a draft.

### Multi-stage comparison conversations

Classify supplied stages neutrally as `source`, `rough cut`, `intermediate edit stage`, `manual fine cut`, or `reference`; AI- or selected-phrase preparation is only an example of an intermediate edit stage. Read [references/rough-fine-stage-flow.md](references/rough-fine-stage-flow.md) for the comparison baselines, report fields, gates, and state transitions.

- Read-only comparison and evidence collection are allowed even when `content_pass` is `draft`.
- Preserve user-saved manual selections and boundaries by default unless the user explicitly asks to revise them. ASR may identify candidates but never authorizes deletion.
- Escalate a fine-cut change to rough-cut review whenever semantic-unit membership or order changes meaning, support, context, Q&A integrity, or any protected fact/relationship. Only nonsemantic local delivery cleanup remains fine-cut work.
- A rough/fine boundary violation reopens `content_pass` as `draft` and adds `human_review`.

## Evidence and decision rules

- Treat subtitle and ASR rows as timing containers, not sentence or idea boundaries. Reconstruct complete semantic units before proposing edits.
- Fix confirmed misheard text before judging whether to cut it. A misspelled name is not a deletion reason.
- In existing-subtitle mode, current visible subtitle text, order, and segmentation are authoritative; ASR is cross-check evidence. In generation mode, require timed transcript evidence. Correct text without changing token or semantic-unit timestamps.
- Use edited audio and waveform evidence to establish boundaries. Waveform thresholds and ASR word timestamps can locate candidates but cannot authorize deletion or splitting by themselves.
- Preserve names, numbers, units, conditions, negations, comparisons, causes, qualifications, relationships, and technical claims. Uncertain or domain-sensitive material stays reviewable.
- Separate the content pass from delivery refinement. Prefer small, local refinement cuts, and never synthesize a statement by stitching unfinished attempts.
- Record a boundary basis, evidence, confidence, and expected join for every destructive decision. When evidence is incomplete or approximate, lower confidence and flag review.
- Evidence verdicts use `PASS|UNVERIFIED` and the weakest supporting tier from [references/verification-levels.md](references/verification-levels.md). Reserve `visual_frame` for current-draft readback supplied through `jianying-editor`.

## Reference routing

Read only the material needed for the selected task:

- Accurate script and recorded takes: [references/copy-first-rough-cut.md](references/copy-first-rough-cut.md).
- Interview or no accurate copy: [references/discovery-rough-cut.md](references/discovery-rough-cut.md).
- Correction and source orientation: [references/transcript-correction-gate.md](references/transcript-correction-gate.md), [references/domain-and-outline.md](references/domain-and-outline.md), and [references/content-analysis.md](references/content-analysis.md).
- Multi-speaker material: [references/dialogue-and-qa.md](references/dialogue-and-qa.md).
- Delivery refinement: [references/speech-cleanup.md](references/speech-cleanup.md), [references/cut-case-law.md](references/cut-case-law.md), and [references/audio-boundaries.md](references/audio-boundaries.md).
- Multi-stage source/rough/intermediate/manual-fine/reference comparison: [references/rough-fine-stage-flow.md](references/rough-fine-stage-flow.md), with sequence evidence in [references/timeline-comparison.md](references/timeline-comparison.md).
- Subtitle proofing/alignment: [references/subtitle-proofreading-and-audio-alignment.md](references/subtitle-proofreading-and-audio-alignment.md) and [references/alignment-plan.md](references/alignment-plan.md).
- Workflow state, report/plan contracts, and automated preparation: [references/workflow-state.md](references/workflow-state.md), [references/decision-plan-schema.md](references/decision-plan-schema.md), [references/analysis-report-schema.md](references/analysis-report-schema.md), [references/verification-levels.md](references/verification-levels.md), and [references/scripted-workflow.md](references/scripted-workflow.md).
- Human-reviewed preferences and dictionaries: [references/preference-and-dictionary.md](references/preference-and-dictionary.md).

## Outputs and handoff

For content editing, produce an evidence summary and a validated content decision plan. Keep delivery-refinement decisions separate from content decisions. Subtitle work uses a separate application-independent alignment plan; generated subtitles remain pending human review. A final-draft audit is read-only.

Validate plans with `python scripts/roughcut_tool.py validate plan <plan.json>` or `python scripts/roughcut_tool.py validate alignment <plan.json>`, as applicable. Use references/scripted-workflow.md for command inputs and preparation details. Perform project mutations only through jianying-editor and only when the user has authorized that mutation; approval of a plan alone does not authorize a write.
