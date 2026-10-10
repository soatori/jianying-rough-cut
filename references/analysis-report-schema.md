# Final-draft analysis report

Validate a report with:

```powershell
python scripts/roughcut_tool.py validate report <report.json>
```

The report is read-only and application-independent. Its text authority is the current rendered final subtitle, not ASR or an older subtitle copy.

Required top-level fields:

```text
report_type
source
evidence
timeline_comparison
semantic_groups
protected_facts
discrepancies
review
```

`source` declares `text_authority`, an approved/stable subtitle reference, and evidence. `timeline_comparison` declares source/target order hashes, sequences, semantic mapping, and `remap_status` (`not_required`, `pending`, `verified`, or `blocked`). Changed order requires a mapping list.

Each semantic group records a stable semantic-unit ID, final subtitle text, one of the shared roles (`hook`, `background`, `question`, `reaction`, `answer`, `evidence`, `technical_detail`, `contrast`, `benefit`, `summary`, `cta`), context dependencies, speaker/function, short-video value, protected-fact flags, listening requirement, and review status.

Wording discrepancies (`subtitle_audio_mismatch`, `asr_final_mismatch`, or
`text_mismatch`) require `review_status: pending` and a `human_review` flag.
Semantic-group and discrepancy `review_status` values are exactly `pending`,
`approved`, or `not_required`; `human_review` is rejected as a status.
A semantic group requiring listening must remain `pending` until its listening
gate is verified. Top-level `review.status` remains `draft`, `review`, or
`approved`. The report cannot contain draft paths, Jianying locators, encryption fields, write-back instructions, or destructive decisions.


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
