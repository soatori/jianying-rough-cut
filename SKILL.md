---
name: jianying-rough-cut
description: "Use for 剪映口播、访谈、教程、讲座等 speech-led video content passes: understand the source, make evidence-backed keep/delete/shorten/reorder decisions, and produce auditable rough-cut and subtitle-alignment plans. Hand approved plans to jianying-editor for project execution. Do not add packaging effects or make unsupported destructive decisions from ASR alone."
---

# Jianying-Intelligent-Rough-Cut

This is the content-intelligence layer for 剪映 speech-led edits. It listens to and understands the source before deciding what the audience should hear, protects technical meaning and continuity, and produces an auditable content plan. It may coordinate with `jianying-editor` for probing and execution of an approved plan, but it never directly mutates a Jianying draft.

## Positioning

- **Owns:** source completeness and orientation, the transcript correction gate (fix misheard text before deciding), semantic segmentation, speaker and Q&A structure, protected facts, Pass 1 content rough-cut decisions, Pass 2 speech refinement, subtitle proofreading/alignment after the edited timeline is saved, and the Pass 3 retrospective that turns human corrections into dictionary, preference, and case-law learning.
- **Produces:** an application-independent content decision plan, a transcript correction table plus unresolved-term list, a repeated-attempt rollup, tiered verification labels, a separate subtitle-alignment plan when that stage is requested, and a Pass 3 learning record.
- **Handoff:** `jianying-editor` resolves approved ranges against the current saved draft and performs safe project operations; `jianying-packaging` starts only after content and subtitle alignment are stable or approved.
- **Does not own:** direct Jianying project writes, flower text, upper-track styling, templates, transitions, overlays, sound effects, or non-speech montage editing. Non-goal: this layer borrows editorial *method* only and never re-implements a proprietary editing runtime (a persistent service, a workbench/Studio UI, a revision-compare-and-swap ledger, forced cloud-only ASR, or a word-id cut store). Project state, probing, and every write belong to `jianying-editor`; this skill only emits validated, application-independent plans.

“Intelligent” means evidence-backed semantic judgment with reviewable uncertainty—not blind deletion based on transcript text, punctuation, or pause length.

The surrounding workflow is `jianying-rough-cut → jianying-editor → subtitle alignment → jianying-packaging`. An orchestration layer may call `jianying-editor` to probe the saved edited timeline and to apply an approved plan, but this skill itself never writes a draft. Use [references/workflow-state.md](references/workflow-state.md) for the shared handoff states.

## Operating modes

Use one explicit mode for each request:

- `content_edit`: analyze source audio/video, decide content structure, and produce an auditable rough-cut or subtitle-alignment plan. This is the default mode.
- `final_draft_audit`: inspect an already saved final or near-final timeline without proposing edits. The current rendered/visible final subtitle is the report's wording authority; ASR, old subtitles, and internal fields are evidence for discrepancies only.

In `final_draft_audit`:

- do not silently replace final subtitle wording with ASR wording;
- mark subtitle/audio disagreements, old-wording remnants, and uncertain technical terms as `human_review`;
- report semantic groups, ordering, packaging mismatches, and evidence only;
- do not emit delete, shorten, reorder, join, or write-back instructions;
- validate the report with `scripts/validate_analysis_report.py`.

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

The following order is required. Do not propose definite deletion, shortening, deduplication, or reordering before the correction gate and the orientation and outline stages are complete.

1. Establish the requested outcome, target audience, platform/pace, duration constraint, and preservation requirements when they affect decisions.
2. Read or listen through the complete available material, perform the material-completeness audit, and record evidence sources and limitations.
3. Run the transcript correction gate in [references/transcript-correction-gate.md](references/transcript-correction-gate.md): correct misheard text against the general and per-user dictionaries (plus a one-time script alignment only when the dictionary cannot settle a term and the speaker's own script exists), and produce the applied-corrections table plus unresolved list before any cut decision. A misheard name is not a deletion reason; fix text first.
4. Complete the content-orientation stage in [references/domain-and-outline.md](references/domain-and-outline.md): identify the theme, thesis, purpose, audience, professional domain, terminology, entities, protected facts, and information outline.
5. If the domain or a technical term is uncertain, mark the affected units for context or human review. For high-stakes domains, verify against authoritative references when appropriate; otherwise do not make a definite destructive decision.
6. Reconstruct complete semantic units across transcript segments. ASR rows and subtitle cues are timing containers, not sentence or idea boundaries.
7. Identify stable speakers and per-unit conversational functions such as host, questioner, respondent, expert, narrator, correction, or supplement. For multi-speaker/Q&A work, read [references/dialogue-and-qa.md](references/dialogue-and-qa.md).
8. Build the original content map before proposing deletions. For detailed criteria, read [references/content-analysis.md](references/content-analysis.md).
9. Produce the first-pass content rough cut. Preserve complete meaning and allow natural breaths, modest pauses, and harmless small repetitions.
10. Audit the proposed cut against the complete source for missing context, altered claims, incorrect question/answer pairing, out-of-order logic, technical-detail loss, and domain terminology loss.
11. Mark the content pass as draft, stable, or approved. Only when it is stable or approved, produce a separate refinement pass for fillers, false starts, repeated openings, stutters, redundant restatements, excess pauses, tiny audio remnants, and hard joins. Run it as five single-criterion scans (one criterion per read) in [references/speech-cleanup.md](references/speech-cleanup.md), apply the case-law in [references/cut-case-law.md](references/cut-case-law.md), and honor the boundary rules in [references/audio-boundaries.md](references/audio-boundaries.md).
12. Output the independent content decision plan described in [references/decision-plan-schema.md](references/decision-plan-schema.md). Do not output an application-specific execution handoff.
13. After the content pass has been executed and the current edited timeline is saved, run the subtitle proofreading and audio-alignment stage in [references/subtitle-proofreading-and-audio-alignment.md](references/subtitle-proofreading-and-audio-alignment.md). Validate the separate [references/alignment-plan.md](references/alignment-plan.md) contract with `scripts/validate_alignment_plan.py` before handing it to `jianying-editor`.
14. After the human reviews the result, run the Pass 3 retrospective in [references/preference-and-dictionary.md](references/preference-and-dictionary.md): diff the approved proposal against the final plan, and archive taste differences to the preference file, corrected proper nouns to the dictionary, and rule gaps to the pending-cases drawer. This stage records learning only; it never mutates a draft.

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

## Two-pass boundary

### Pass 1: content rough cut

Optimize correctness, structure, and completeness. Remove clear digressions, failed takes fully covered by a complete take, large redundant passages, and content outside the agreed scope. Keep uncertain material for review.

This pass may retain natural breaths, short thinking pauses, contextual discourse markers, and small repetitions that do not impair understanding.

### Pass 2: rough-cut refinement

After Pass 1 is approved or stable, tighten delivery at phrase and audio-boundary level. Prefer small local cuts over deleting whole sentences. Preserve one natural connector when repeated openings are reduced. Compress pauses rather than forcing speech to zero gap.

Every refinement candidate must be re-auditioned in context. A clean transcript does not prove a natural audio join.

The plan must record the phase status separately: `workflow.content_pass` is `draft`, `stable`, or `approved`; `workflow.refinement_pass` is `not_started`, `draft`, or `approved`. Refinement decisions are not valid while the content pass is still draft.

### Pass 3: retrospective (learning only)

Passes 1 and 2 are the only cutting passes; Pass 3 does not edit content. After the human reviews an executed result, run the retrospective in [references/preference-and-dictionary.md](references/preference-and-dictionary.md): diff the approved proposal against the final plan and persist restored cuts, missed cuts, and the dictionary/preference/pending-case updates they imply. It is gated by `content_pass` being `stable` or `approved` and never mutates a draft or a shipped plan.

## Decision rules

- Edit complete semantic units unless the defect is a local filler, false start, stutter, or pause.
- Do not stitch unfinished fragments from different attempts into a synthetic statement. A later take is not automatically better; keep the complete, natural, accurate, contextually connected version.
- Repetition, discourse markers, and overlap: remove only when no new premise, emphasis, emotion, contrast, clarification, condition, or speaker contribution is lost. Criteria in [references/speech-cleanup.md](references/speech-cleanup.md) and [references/dialogue-and-qa.md](references/dialogue-and-qa.md).
- Reordering moves complete semantic units. Recheck pronouns, connectors, chronology, causal dependencies, and domain conditions afterward.
- Record start/end boundary basis for every decision. Exact timestamps when evidence permits; approximate boundary on a destructive action must remain reviewable and may not be high-confidence.
- Boundary evidence and picture-lock rules: [references/audio-boundaries.md](references/audio-boundaries.md) and [references/content-analysis.md](references/content-analysis.md). Do not infer frame-accurate boundaries from vague instructions alone. Picture-lock only where a shot boundary carries a real semantic constraint.
- Time thresholds may flag pause candidates but may not authorize deletion by themselves.
- When evidence is insufficient, use `needs_listen`, `needs_context`, `low_confidence`, or `human_review`; do not convert uncertainty into a delete instruction.
- A cut decision is binary: commit it as `delete`/`shorten`/`reorder`/`join` after self-verification, mark it `review`, or drop it. Do not emit a "suggest deleting, awaiting the user" third state or ask line by line. Risk changes only how hard you verify, not the shape of the output. If you cannot confirm after re-reading in context, leave the unit out (`拿不准 = 不列为删除`). A `review` decision keeps the unit in place pending a listening/context judgment about whether it belongs; it is never a committed deletion waiting for a nod.
- Before presenting the plan, re-read the post-cut text in playback order and revoke any line that no longer reads through. Self-verification means you re-reading it against the audio and context, not forwarding the decision to the user. A clean transcript never proves a natural join.
- When material is partial or unknown, do not mark an affected delete, shorten, reorder, or join as high-confidence. Add a review flag to lower-confidence candidates.
- When a decision touches a domain-sensitive fact, terminology, number, unit, condition, or entity, record that sensitivity and retain the evidence.
- Subtitle recognition text is evidence, not truth. Correct current saved subtitles against edited-timeline audio before packaging; do not use an older subtitle copy as the write source.
- Record `audio`, `picture`, or `manual` mode plus boundary basis, evidence, confidence, and review state for both ends of every aligned subtitle unit (see [references/alignment-plan.md](references/alignment-plan.md)).
- When the workflow mode is `final_draft_audit`, declare `final_visible_subtitle` as the text authority and keep all ASR/final-text differences reviewable; do not turn them into corrections inside this skill.
- Waveform thresholds locate candidates; they never authorize deletion or splitting by themselves. Word-level timestamps are cross-check evidence and require a health check.

## Required outputs

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

Run `scripts/validate_plan.py <plan.json>` to validate the content decision plan before presenting it for review.
