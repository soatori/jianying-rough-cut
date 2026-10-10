# Automation and human-intervention boundary

Use this boundary to reduce repetitive search, transcription, comparison, and
candidate-generation work without moving editorial authority away from the
human reviewer.

## Priorities

| Priority | Work | Why it is automatable | Human role that remains |
| --- | --- | --- | --- |
| P0 | Repetition, false starts, retakes, fillers | Deterministic scans produce a bounded candidate list | Confirm contextual meaning and approve any deletion |
| P0 | Pause and waveform candidates | Thresholds and waveform evidence locate candidates | Classify function and audition the result |
| P0 | Confirmed transcript corrections | Dictionaries apply known names, models, numbers, and units | Resolve unknown or domain-sensitive terms |
| P0 | Playback mapping, stage comparison, subtitle boundary candidates | Order, timing, and waveform relationships are structured data | Designate authority/baselines and listen at flagged edges |
| P1 | Semantic-unit pre-segmentation | Transcript and timing seeds reduce manual organization | Check completeness, topic boundaries, and dependencies |
| P1 | Speaker turns and Q&A mapping | Turn-taking and question/answer markers can be proposed | Confirm cross-turn context and missing setup |
| P1 | Protected-fact candidates | Patterns can surface names, numbers, units, conditions, and technical claims | Verify facts and approve any content change |
| P2 | Thesis, audience, topic, and paragraph relations | Agent summaries can prepare a review draft | Approve the editorial interpretation |
| P2 | Negation, comparison, causality, qualification, and technical claims | Agent can flag risky language | Confirm meaning and risk; never auto-approve |
| No gate reduction | Content deletion, semantic reordering, final listening, manual-fine-cut revision | Scripts can only provide evidence or proposals | Explicit human approval remains mandatory |

## Intervention levels

- **Deterministic preparation:** `preflight`, dictionary correction, playback
  mapping, candidate scans, waveform extraction, subtitle candidate alignment,
  stage comparison, and report validation may run without semantic approval.
- **Agent interpretation:** semantic units, topic structure, Q&A relationships,
  protected-fact exposure, pause-function candidates, and cut-risk explanations
  require Agent reasoning and recorded provenance.
- **Human gates:** `content_pass` promotion, domain-term confirmation,
  `human_listening`, destructive joins or pause changes, protected-fact
  decisions, and final acceptance remain human-owned.

## Non-negotiable boundaries

- Scripts and scans reduce manual searching; they do not authorize deletion,
  splitting, joining, reordering, or pause removal.
- Agent interpretation reduces manual organization; it does not create
  `human_verified` evidence or clear `human_listening`.
- Unknown or `unavailable` semantic risk is not evidence that a destructive
  refinement is nonsemantic.
- Preserve complete semantic units, technical conditions, facts, Q&A
  relationships, and user-saved manual choices.
- A semantic membership or order change returns to rough-cut review even when
  the physical edit is small.
- `stage_comparison` remains read-only; automation cannot turn a comparison
  report into an edit plan.
- Reduce repeated inspection first; do not reduce approval gates to improve a
  scripted-rate metric.

## Recommended route

Run deterministic preparation first, then ask the Agent for structured
interpretation and risk candidates, then request human confirmation for the
unresolved and destructive decisions. Keep script, Agent, and human provenance
separate in reports so a successful command is never mistaken for editorial
approval.
