# Final-draft analysis report

Validate a report with:

```powershell
python scripts/validate_analysis_report.py <report.json>
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

Discrepancies involving wording or audio must remain `human_review`. The report cannot contain draft paths, Jianying locators, encryption fields, write-back instructions, or destructive decisions.
