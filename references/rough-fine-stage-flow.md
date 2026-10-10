# Multi-stage comparison conversation flow

Use this flow when a user supplies more than one edit stage. It compares `source`, `rough cut`, `intermediate edit stage`, `manual fine cut`, and `reference` material without collapsing content planning into delivery cleanup. Automated or phrase-selected preparation is only an example of an intermediate edit stage.

## Stage contract

| Stage | Owns | Does not own |
| --- | --- | --- |
| `source` | Complete material, chronology, original wording, technical conditions | Editorial order or target length |
| `rough cut` | Theme, thesis, complete semantic units, content selection, semantic order, block-level segmentation | Word-level polish or final audio joins |
| `intermediate edit stage` | Mechanical pause compression candidates, false-start candidates, phrase-level preparation | Authority to redefine the thesis or remove protected content |
| `manual fine cut` | Nonsemantic local delivery cleanup, visual breathing, local joins, preserved manual choices | Silent redefinition of rough-cut scope, semantic-unit membership, or semantic order |
| `reference` | Comparison evidence, such as wording or timing | Proof that an audio join sounds correct or authority that was not user-designated |

Do not infer roles or authority from stage names. If labels are ambiguous, batch one intake question that identifies the candidate stages and asks for their roles and the user-designated current manual stage.

## Inputs, questions, and authority

- Requested comparison fields depend on the requested scope. Batch related questions and ask only when required information is missing. Direct read-only comparison may proceed when all requested inputs are supplied.
- Preserve user-saved manual selections and boundaries by default unless the user explicitly asks to revise them. ASR may identify candidates but never authorizes deletion.
- Report authority as `unknown` when it is not explicitly designated. Never infer authority from stage names or apparent edit order.
- Route source-plus-subtitle-only work to `subtitle_alignment`; do not invent multi-stage authority.
- Read-only evidence collection and comparison remain allowed while `content_pass` is `draft`.

## Comparison baselines

Use the baseline that answers the requested question:

| Comparison purpose | Baseline |
| --- | --- |
| Content loss or completeness | `source` |
| Stage-to-stage delta | the user-designated preceding accepted stage; if none is designated, `unavailable` |
| Preservation or authority comparison | the user-designated current manual stage |

State the selected baseline in the report. A preceding accepted stage must be explicitly designated by the user; do not infer acceptance, sequence authority, or baseline status from stage names or apparent edit order. If no preceding accepted stage is designated, mark the stage-to-stage baseline and affected comparison `unavailable`; do not substitute another baseline silently. If any other required baseline is unavailable, mark the affected comparison `unavailable` as well.

## Conversation flow

`stage_comparison` is read-only and ends with the comparison report. It must not enter fine-cut direction, cleanup candidates, proposed changes, or other edit planning. Run the follow-on planning below only as `content_edit`, in a separate invocation after the user explicitly requests it.

### Stage-comparison flow

1. **Intake and authority**
   - Classify every supplied stage as `source`, `rough cut`, `intermediate edit stage`, `manual fine cut`, or `reference`.
   - Identify the requested comparison scope, required baselines, target audience, target length, platform, and whether visual breathing is intentional.
   - Record whether the manual fine cut is the current authority, a target, or only a reference. If not supplied, record authority as `unknown`.
   - Record the user-designated preceding accepted stage when stage-to-stage deltas are requested. If none is designated, use baseline `unavailable`; do not infer acceptance or authority.

2. **Evidence collection**
   - Gather source ranges, stage order, semantic-unit mappings, subtitle/ASR evidence, waveform evidence, and current-draft readback only as the requested scope requires.
   - This stage is read-only and may run with `content_pass: draft`.
   - Missing source or unresolved terms may leave review candidates, but they block high-confidence destructive decisions for the affected material.

3. **Read-only comparison report and stop**
   - Produce one requested-scope comparison report using the comparison inventory defined below.
   - Keep it read-only: do not include fine-cut direction, cleanup candidates, proposed changes, or final auditory success claims.
   - `human_review` is a review flag on affected decisions or report rows, not a workflow state.
   - Stop after delivering this report. Transition to edit planning only through a separate `content_edit` request.

### Optional content_edit follow-on planning

Run steps 4-7 only in `content_edit` after explicit user direction. Never continue automatically from `stage_comparison`.

4. **Rough-cut direction gate (`content_edit`)**
   - Build the whole-source orientation first: thesis, audience, domain, speakers, dependencies, relationships, and protected facts.
   - Present keep/drop candidates at semantic-block level, including role, source range, added information, and required context.
   - Ask one combined block-level direction question covering theme priority, keep/drop scope, order, and target shape. Do not ask for approval on every physical cut.
   - Do not issue new destructive fine-cut recommendations or final auditory success claims while `content_pass` is `draft`; this gate does not block read-only evidence collection or comparison.

5. **Rough-cut review and state (`content_edit`)**
   - Report the proposed blocks in playback order and re-read the retained material as a complete narrative.
   - Check for lost premises, broken questions and answers, missing technical conditions, altered causality, comparisons, relationships, and orphaned references.
   - Set `content_pass: draft` after evidence collection, `stable` after the agent's semantic self-audit, and `approved` only after explicit user approval.
   - A rough/fine boundary violation reopens `content_pass` as `draft` and adds the `human_review` flag to affected decisions and report rows; `human_review` is not a workflow state.

6. **Optional content_edit fine-cut direction and cleanup**
   - New destructive fine-cut recommendations require `content_pass: stable` or `approved`; ask only for missing refinement constraints: speech density, pause tolerance, acceptable visual breathing, protected facts and relationships, and join-risk tolerance.
   - Distinguish intended silent visuals from unrecognized speech, room tone, off-mic speech, and edit damage. A no-ASR span is not proof of silence.
   - Flatten each edit in playback order using source ranges and remapped semantic-unit IDs.
   - Classify changes as copied, shortened, deleted, reordered, joined, appended, or unchanged.
   - Separate semantic paragraphs from physical cuts: many micro-cuts may express one paragraph, and one long segment may contain several paragraphs.
   - Run delivery cleanup by separate scans for repetition, false starts, corrected retakes, stutters, and fillers; then review pauses and joins in context.
   - Preserve complete meanings and all protected facts and relationships unless rough-cut scope is explicitly reopened.

7. **Optional content_edit fine-cut review**
   - Return one report containing both the semantic/cut-risk section and the shared comparison inventory defined below.
   - Do not report a join, pause, or no-ASR transition as successful without `human_listening` evidence.
   - Have a human audition proposed changes where possible and record the verdict. Agent playback or waveform analysis does not clear `human_listening`; without a person's recorded verdict, keep it pending.

## Pause ownership in content planning

These planning rules apply only to content_edit. stage_comparison may report existing pause evidence but must not propose pause changes.

- Classify pauses by function: hesitation, sentence boundary, speaker handoff, topic shift, emphasis, emotional beat, breath, failed-take gap, or edit damage.
- Intermediate pause work records and proposes candidates; it does not authorize destructive pause changes.
- A destructive pause change requires waveform localization plus a recorded human `human_listening` verdict.
- Default to local compression rather than removal. Preserve enough room for articulation, speaker handoff, topic changes, contrast, and emphasis.
- A pause duration threshold is a detector, not a deletion rule.
- Review before, across, and after every destructive join. Check clipped consonants, duplicated fragments, clicks, room-tone discontinuity, overlap, reversed source order, and unnaturally accelerated delivery.
- If a fine cut changes order, duration, or membership, remap semantic-unit IDs and context before reusing any earlier timecode.

## Protected facts and rough/fine boundary

Protected facts include names, numbers, units, conditions, negations, comparisons, causes, qualifications, relationships, and technical claims.

Escalate a fine-cut change to rough-cut review whenever semantic-unit membership or order changes meaning, support, context, Q&A integrity, or any protected fact/relationship. Only nonsemantic local delivery cleanup remains fine-cut work.

## Required reports

Fields are required only when they fall within the requested comparison scope. Every required field must be present with evidence or explicitly marked `not_assessed` or `unavailable`; never fabricate counts or relationships.

### Shared comparison inventory

For each supplied stage:

- canonical role, authority (`yes`, `no`, or `unknown`), duration, and segment count;
- the selected comparison baseline;
- containment, overlap, deletion, addition, and reorder relationships to that baseline;
- pause-removal evidence by functional class, not only duration;
- no-ASR or visually dominated spans;
- protected-fact and unresolved-term exposure;
- the verdict for each required relationship or claim.

Use `not_assessed` when a field is outside the requested scope. Use `unavailable` when a required field cannot be evaluated from the supplied inputs. Do not infer missing counts, relationships, or authority.

### Read-only comparison report (`stage_comparison`)

Use the shared comparison inventory. This report remains read-only and contains no fine-cut direction, cleanup candidates, or proposed changes. Deliver it and stop.

### Optional content_edit fine-cut review report

Keep the semantic/cut-risk section and the shared comparison inventory in one report. This report is optional follow-on planning for `content_edit` only.

#### Semantic and cut-risk section

- semantic-unit membership and order changes, with their effect on meaning, support, context, Q&A integrity, and protected facts/relationships;
- semantic paragraph count versus physical cut count;
- selected source clusters and large narrative jumps;
- risky joins and their before/across/after review status.

## Evidence verdicts

- Every verdict uses `PASS|UNVERIFIED`.
- Apply the weakest-tier rule from [verification-levels.md](verification-levels.md).
- `visual_frame` is reserved for current-draft readback supplied through `jianying-editor`; application-independent planning or screenshots from another surface do not qualify.
- Without a recorded human listening verdict, auditory conclusions remain `UNVERIFIED` and `human_listening` stays pending. Agent playback or waveform analysis cannot clear it.

## Generalization boundary

Keep this reference free of project names, copy, assets, IDs, absolute paths, timecodes, colors, and case-specific decisions. Worked case material belongs in external case references or conversation memory, not in this reusable Skill.
