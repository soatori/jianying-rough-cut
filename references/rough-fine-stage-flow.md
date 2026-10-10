# Source-to-fine comparison conversation flow

Use this flow when a user supplies more than one edit stage—typically source material, a rough cut, an optional AI or selected-phrase pass, and a manually edited fine cut. It defines how to discuss and compare stages without collapsing content planning into delivery cleanup.

## Stage contract

| Stage | Owns | Does not own |
| --- | --- | --- |
| Source | Complete material, chronology, original wording, technical conditions | Editorial order or target length |
| Rough cut | Theme, thesis, complete semantic units, content selection, major order, block-level segmentation | Word-level polish or final audio joins |
| Optional AI / selected-phrase pass | Mechanical pause compression, false-start candidates, phrase-level fragmentation | Authority to redefine the thesis or remove protected content |
| Manual fine cut | Delivery density, local cleanup, visual breathing, final joins, preserved manual choices | Silent redefinition of rough-cut scope or order |
| Reference / subtitle track | Wording or timing evidence only | Proof that an audio join sounds correct |

Do not infer roles from timeline names alone. If labels are ambiguous, ask one intake question naming the candidate timelines and ask which are source, rough, optional intermediate, manual fine, and reference.

## Conversation flow

1. **Intake and authority**
   - Identify every supplied stage and whether the manual fine cut is a reference, a target, or merely a comparison.
   - Record target audience, target length, platform, and whether visual breathing is intentional.
   - Treat user-saved manual edits as current editorial evidence. Manual selections and saved boundaries outrank ASR-derived deletion proposals; ASR never authorizes an automatic deletion.

2. **Rough-cut direction gate**
   - Build the whole-source orientation first: thesis, audience, domain, speakers, dependencies, and protected facts.
   - Present keep/drop candidates at semantic-block level, including role, source range, added information, and required context.
   - Ask one combined block-level direction question covering theme priority, keep/drop scope, order, and target shape. Do not ask for approval on every cut.
   - Do not enter fine-cut discussion while the rough-cut content pass is `draft`.

3. **Rough-cut review**
   - Report the proposed blocks in playback order and re-read the retained material as a complete narrative.
   - Check for lost premises, broken questions and answers, missing technical conditions, altered causality, and orphaned references.
   - Mark the content pass `draft`, `stable`, or `approved`. Major content deletion or reordering later found in a fine cut returns to this stage.

4. **Fine-cut direction gate**
   - Once rough content is `stable` or `approved`, ask only for missing refinement constraints: speech density, pause tolerance, acceptable visual breathing, protected names/numbers/units, and join-risk tolerance.
   - Distinguish intended silent visuals from unrecognized speech, room tone, off-mic speech, and edit damage. A no-ASR span is not proof of silence.
   - Confirm which manual fine-cut choices must remain authoritative before proposing changes.

5. **Fine-cut comparison and cleanup**
   - Flatten each edit in playback order using source ranges and remapped semantic-unit IDs.
   - Classify changes as copied, shortened, deleted, reordered, joined, appended, or unchanged.
   - Separate semantic paragraphs from physical cuts: many micro-cuts may express one paragraph, and one long segment may contain several paragraphs.
   - Run delivery cleanup by separate scans for repetition, false starts, corrected retakes, stutters, and fillers; then review pauses and joins in context.
   - Preserve complete meanings, names, numbers, units, conditions, negations, causes, qualifications, and question-answer pairs unless rough-cut scope is reopened.

6. **Fine-cut review**
   - Return a semantic section map, a cut/join risk table, pause-policy summary, and listening checklist.
   - Tag every conclusion with `plan_consistency`, `visual_frame`, or `human_listening`.
   - Do not report a join, pause, or no-ASR transition as successful without `human_listening` evidence.

## Pause and join policy

- Classify pauses by function: hesitation, sentence boundary, speaker handoff, topic shift, emphasis, emotional beat, breath, failed-take gap, or edit damage.
- Default to local compression rather than removal. Preserve enough room for articulation, speaker handoff, topic changes, contrast, and emphasis.
- A pause duration threshold is a detector, not a deletion rule. It cannot authorize removal without waveform localization plus listening judgment.
- Review before, across, and after every destructive join. Check clipped consonants, duplicated fragments, clicks, room-tone discontinuity, overlap, reversed source order, and unnaturally accelerated delivery.
- If a fine cut changes order, duration, or membership, remap semantic-unit IDs and context before reusing any earlier timecode.

## Required comparison output

For each supplied stage, report:

- role, duration, segment count, and whether it is current authority;
- containment, overlap, deletion, addition, and reorder relationships to the comparison baseline;
- semantic paragraph count versus physical cut count;
- selected source clusters and large narrative jumps;
- pause-removal evidence by functional class, not only duration;
- no-ASR or visually dominated spans;
- protected-fact and unresolved-term exposure;
- risky joins and the weakest evidence tier supporting each verdict.

## Rough/fine boundary

A fine cut may shorten local delivery, remove failed takes, tighten pauses, and polish joins. It must return to rough-cut review when it removes a complete argument, changes thesis scope, changes major order, breaks a question-answer pair, or discards a protected technical condition.

## Generalization boundary

Keep this reference free of project names, copy, assets, IDs, absolute paths, timecodes, colors, and case-specific decisions. Worked case material belongs in external case references or conversation memory, not in this reusable Skill.
