# Speech cleanup: five single-criterion scans

Refinement (Pass 2) is run as five separate reads of the same material in **playback order**, carrying one criterion each. Reading once with six criteria in mind is measurably worse than five focused passes; each pass produces a small, checkable set of candidates. A candidate found in an earlier pass is not re-touched by later passes; conflicts are resolved in the summary step.

Precedence of judgment sources: **user preference > user case-law > general case-law > the defaults below.** Rules live here; worked examples live in [cut-case-law.md](cut-case-law.md).

## The five scans

1. **Repetition.** Inter-sentence and intra-sentence repeats are candidates for contextual review. Near-identical adjacent attempts may still add information; duration or text similarity cannot choose a deletion. Whole-sentence and divergent-retake repeats are high risk: keep them in the repeated-attempt rollup (see below).
2. **False starts and self-corrections.** A fragment apparently abandoned mid-way, or a re-said line that restarts the same thought, is a candidate. Check the complete version and preserve natural connectors before planning a change.
3. **Misspoken retakes (wrong number / wrong name).** A wrong fact or proper noun that the speaker later restates correctly requires protected-fact review before any content decision. A name *misheard by ASR but said once correctly* is a correction-gate item ([transcript-correction-gate.md](transcript-correction-gate.md)), never a deletion.
4. **English stutters.** Repeated word-initials, letters, or syllables in English tokens (do not match only Chinese). Cut at word level only when consonant/vowel boundaries and prosody permit a clean splice.
5. **Fillers and discourse markers.** The most subjective; tune density and tolerance to the preference file. A single natural particle (e.g. "呢", "那个", "well") is conservatively kept — deleting it makes delivery feel fake. Only a run of two-plus meaningless particles is a group low-risk candidate.

## Fillers and discourse markers

No token is an unconditional blacklist. "Then", "so", "actually", "right", "this" can carry structure, stance, response, reference, or emotion. Delete only when the semantic contribution is empty **and** the resulting audio stays natural. If removal produces a hard splice, keep it or shorten only the adjacent pause.

## Repeated-attempt rule

1. Confirm the attempts express the same intended idea.
2. Identify the complete version — the one with the necessary subject, setup, transition, qualifier, and conclusion.
3. Remove only abandoned, wrong, dangling, or fully covered material.
4. Prefer complete + accurate + natural + well connected. Do not mechanically keep the last take, and do not keep the shortest.

When several attempts each add independent information, that is not repetition — it is complement; keep both and do not list them as candidates.

## Pass separation and the two-state rule

Keep content structure auditable without dozens of word-level cuts. Pass 2 owns nonsemantic local delivery cleanup. Any change to semantic-unit membership, semantic order, or protected facts returns to rough-cut review, even when the physical edit is tiny. Unresolved candidates and joins stay `review`; neither a detector nor agent self-verification clears human listening.

## Pause candidates and semantic risk

Pause review follows the five scans; it is not another text-deletion rule.
The exact functional labels are `hesitation`, `sentence_boundary`,
`speaker_handoff`, `topic_shift`, `emphasis`, `emotional_beat`, `breath`,
`failed_take_gap`, and `edit_damage`. See [audio-boundaries.md](audio-boundaries.md)
for their contextual meanings and candidate fields. Pause length and function
are separate: no duration threshold can classify a pause or choose a cut.

Decision records may supply `semantic_risk` with `membership_change`,
`order_change`, and `protected_fact_impact`. Each field is a boolean, or
`unavailable` when required evidence is missing, or `not_assessed` when outside
scope. If supplied, include all three; omission is not a negative assessment.
Any `true` requires `escalate_to_rough_cut: true`, `human_review: true`, and
`pass: content`. An explicit `reorder` also establishes order risk. Review the
semantic units and reopen `content_pass: draft` before further fine-cut work.
All three `false` leaves nonsemantic local cleanup eligible for refinement,
subject to stable content, boundary evidence, and the existing listening gates.
Unknown risk never proves a change nonsemantic.

The decision validator returns effective risk and escalation under
`review_gates["decisions[index]"]`, without changing the input. Missing risk is
reported as `unavailable`. It rejects missing escalation flags, semantic changes
left in refinement, and structured automatic-action instructions. Candidate-only
or `script_generated` records cannot carry destructive actions. A reviewed
content plan may still state a proposed action; validation never executes it.

## Summary and self-read

After the five scans, merge into:

- the **refinement decision table** (one row per candidate: range, scan type, review status, proposed retained reading, semantic risk, evidence); and
- the **repeated-attempt rollup** (which line, how many times, which kept, which removed, risk) — because a per-word table cannot show take counts, which is exactly what a human most wants to check. See [content-analysis.md](content-analysis.md).

Then read the proposed retained text once more in playback order and revoke any line that no longer reads through. Semantic risk changes review ownership; unresolved evidence remains reviewable rather than becoming an automatic delete or join instruction.
