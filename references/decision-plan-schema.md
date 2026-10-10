# Independent content decision plan schema

This schema describes editorial analysis only. It contains no application-specific execution command, timeline mutation field, or project-file handoff.

Subtitle correction and timing alignment is a separate contract. After the content plan has been executed on the current saved timeline, create and validate [alignment-plan.md](alignment-plan.md) with `python scripts/roughcut_tool.py validate alignment <plan.json>`; do not add Jianying locators to this content schema.

## Required top-level fields

- `version`: currently `1`
- `input`: media identity, timebase, optional duration, and a required completeness audit
- `evidence`: evidence sources and limitations
- `goal`: requested outcome and preservation constraints
- `theme_analysis`: topic, thesis, purpose, audience, and confidence
- `domain_analysis`: domain status, primary domain, terminology, entities, and confidence
- `outline`: source information outline and confidence
- `speakers`: stable identities, roles, and confidence
- `original_structure`: ordered source units
- `recommended_structure`: ordered proposed units
- `decisions`: Pass 1 and Pass 2 decisions
- `protected_facts`: details that must survive review
- `workflow`: mode plus content/refinement phase status and gate

The surrounding workflow also tracks `subtitle_alignment` as `not_started`, `draft`, `stable`, or `approved`, but the alignment units live in the separate `subtitle_alignment_plan` rather than in this content decision plan.

`theme_analysis`, `domain_analysis`, and `outline` must each include `confidence` with `high`, `medium`, or `low`.

## Material completeness and phase gate

`input.completeness` is required and contains:

- `status`: `complete`, `partial`, or `unknown`;
- `checked`: a non-empty list of checked sources such as `video`, `audio`, `transcript`, or `subtitle_timing`;
- `missing`: a list of missing sources or evidence;
- `evidence`: a non-empty list explaining how completeness was assessed;
- `impact`: `none` when the material is complete, otherwise `review_required`.

`workflow` is required. `subtitle_alignment` is optional for a content-only plan and defaults to `not_started`; use the separate alignment plan before packaging:

```json
{
  "content_pass": "stable",
  "refinement_pass": "draft",
  "subtitle_alignment": "not_started"
}
```

`workflow.mode` defaults to `content_edit` and may be `content_edit` or `final_draft_audit`. An audit plan must also set `workflow.text_authority` to `final_visible_subtitle`. Audit mode is read-only: its decisions may be `keep` or `review`, but never `delete`, `shorten`, `reorder`, or `join`. For a full final-draft report, use [analysis-report-schema.md](analysis-report-schema.md) rather than turning the audit into an edit plan.

`content_pass` is `draft`, `stable`, or `approved`. `refinement_pass` is `not_started`, `draft`, or `approved`. A refinement decision is valid only when `content_pass` is `stable` or `approved` and `refinement_pass` is not `not_started`.

## Content orientation

```json
{
  "theme_analysis": {
    "topic": "human-readable topic",
    "thesis": "one-sentence central proposition",
    "purpose": "interview|explanation|tutorial|discussion|other",
    "audience": "expected audience and knowledge level",
    "confidence": "medium",
    "alternatives": []
  },
  "domain_analysis": {
    "status": "identified|uncertain|not_applicable",
    "primary_domain": "domain or general",
    "confidence": "medium",
    "segments": [],
    "terms": [],
    "entities": [],
    "protected_facts": [],
    "unresolved_terms": []
  },
  "outline": {
    "confidence": "medium",
    "modules": [],
    "units": []
  }
}
```

Each outline unit should record its time range, title or summary, role, speaker or speakers, dependencies, information added, domain risk, and transcription confidence. The validator requires at least an ID, title/summary, role, time range, timebase, and confidence for each unit.

Highlight groups may be recorded as a separate report handoff. Use the shared roles `hook`, `background`, `question`, `reaction`, `answer`, `evidence`, `technical_detail`, `contrast`, `benefit`, `summary`, and `cta`. Keep their semantic-unit references and protected-fact flags; do not add packaging coordinates or effects to this schema.

## Decision

Each decision includes:

- `id`;
- `pass`: `content` or `refinement`;
- `speaker_id` when known;
- `start`, `end`, and `timebase`;
- `boundary`: start/end boundary basis, supporting evidence, and precision;
- `summary` and `reason`;
- `action`: `keep`, `delete`, `shorten`, `reorder`, `join`, or `review`;
- `confidence`: `high`, `medium`, or `low`;
- `flags`: zero or more of `needs_listen`, `needs_context`, `low_confidence`, `human_review`;
- `domain_sensitive`: whether the decision touches a professional fact, term, entity, number, unit, condition, or qualifier;
- `expected_join` when continuity changes;
- `protected`: facts or relationships touched by the decision.

All decision time ranges use the `input.timebase`. If `input.duration` exists, ranges must remain inside it. A decision involving unresolved domain-sensitive material may not be a high-confidence destructive action.

The `boundary` object is required for every decision:

```json
{
  "start_basis": "phrase_boundary",
  "end_basis": "pause",
  "evidence": ["audio", "transcript"],
  "precision": "exact",
  "note": "The cut ends after the speaker completes the qualification."
}
```

Valid boundary bases are `semantic_unit`, `word_boundary`, `phrase_boundary`, `sentence_boundary`, `pause`, `waveform`, `shot_boundary`, `take_boundary`, `manual_marker`, `derived`, and `unknown`. A destructive decision with `precision: approximate` cannot be high-confidence and should carry a review flag.

When `input.completeness.status` is `partial` or `unknown`, destructive decisions cannot be high-confidence. Lower-confidence affected decisions should carry `needs_context`, `low_confidence`, or `human_review`.

## Independence rule

Plans must not contain `execution_handoff` or application-specific `keep_blocks`. A content plan may be reviewed, revised, or manually translated into another system later, but this schema does not define that translation.

A domain-sensitive destructive decision (`delete`, `shorten`, `reorder`, or
`join`) cannot have `confidence: high` when `domain_analysis.status` is
`uncertain`, domain confidence is `low`, or `unresolved_terms` is non-empty.
Review flags and human-verification claims do not override this restriction.


## Provenance and human-review gates

Every evidence or interpretation object may declare `provenance` using exactly
`script_generated`, `agent_interpreted`, `human_verified`, or `unavailable`.
The field is optional for compatibility. Omission means `unavailable`, never
`script_generated` merely because a CLI report exists. Provenance is local to
that object: parent provenance and verdicts do not verify child rows.
`script_generated` describes deterministic evidence; `agent_interpreted`
describes agent interpretation. Neither grants human authority.

`human_verified` requires an externally recorded, approved `human_verdict` on
that same object. A verdict is an object with these required fields:

- `actor`: exactly `human`;
- `reviewer`: non-empty string identifying the human reviewer;
- `verdict`: exactly `approved` or `rejected`;
- `scope`: exactly `evidence`, `interpretation`, or `human_listening`;
- `evidence`: non-empty string recording or referencing the human verdict.

A script/agent report, a review flag, a reviewer name alone, or an approval on
another object is insufficient. Producers must record an actual human verdict;
they must never manufacture one from playback or waveform analysis. Validation
checks the supplied attestation's structure and scope, not the reviewer's identity
or authenticity. A rejected verdict is valid as a record but cannot verify anything.

`human_listening` is exactly `pending`, `verified`, `not_assessed`, or
`unavailable`, and defaults to `pending`. Only explicit `verified` with an
approved same-object verdict whose scope is `human_listening` clears the gate.
A verdict about evidence or interpretation cannot clear listening. Use
`not_assessed` only for out-of-scope listening and `unavailable` for required
evidence that cannot be evaluated; when `needs_listen` is true or appears in
`flags`, listening must stay `pending` until verified. Agent playback and
waveform analysis cannot clear this gate.

`human_review` is an optional boolean flag, also expressible as `human_review`
in the existing `flags` array. It is never a workflow or review status, never
an approval, and does not itself clear listening. When both flag forms are
present, either true form marks the row for human review.

The existing validation result retains `ok`, `errors`, `warnings`, and counts,
and adds `review_gates`: a mapping from object paths to effective `provenance`,
`human_listening`, and boolean `human_review`. All input objects are represented,
including nested evidence and interpretation rows; the root path is `root`.
Verdict records themselves are excluded. The validator does not modify the input.
Invalid claims fail validation; unsupported provenance or unsubstantiated
`human_verified` is reported effectively as `unavailable`, and unsubstantiated
listening verification remains `pending`. A successful schema check alone is
not completed human review.

## Semantic escalation and refinement handoff

`semantic_risk` records `membership_change`, `order_change`, and
`protected_fact_impact` as booleans, `unavailable`, or `not_assessed`.
Omitted risk evidence remains `unavailable`. A destructive refinement decision
requires all three fields to be explicitly assessed as `false`. Missing,
unavailable, or out-of-scope assessment cannot authorize destructive refinement,
even with a human verdict; retain an `action: review` record until assessment is
available. Validation marks blocked destructive refinement for human review.
Non-destructive `keep` and `review` records remain compatible with omitted or
unknown risk evidence.

Semantic changes require `escalate_to_rough_cut: true`, `human_review: true`,
and the content pass. A `reorder` action always implies `order_change: true`.
An unresolved destructive escalation requires `workflow.content_pass: draft`,
`workflow.refinement_pass: not_started`, and `workflow.subtitle_alignment` set
to `not_started` or `draft`. Other refinement decisions cannot remain valid
while the content pass is reopened. Validation rejects stale workflow states;
it does not mutate the submitted plan or automatically approve any stage.

Only an approved, structurally valid `human_verdict` with `scope: interpretation`
on the escalated decision itself resolves this workflow restriction. Evidence
or listening verdicts, rejected verdicts, parent approvals, and approvals on
other decisions do not resolve it. Every destructive escalation must be resolved
before downstream approval can validate. Resolution leaves the semantic decision
in the content pass and does not clear pending human listening. These extra
workflow restrictions apply to destructive proposals; non-destructive records
retain their existing validation behavior.
