# Learning report contract

`learning_report` is an application-independent record of human-reviewed
patterns. It is a learning signal, not a draft mutation and not a replacement
for the user preference or dictionary files.

The report, source, and entry objects use closed field sets. Each entry may
contain only:

- `area`: `rough_cut`, `subtitle_alignment`, `packaging`, `motion`, `audio`, or `handoff`;
- `pattern`: a project-independent behavior to evaluate;
- `evidence_level`: `plan_consistency`, `visual_frame`, or `human_listening`;
- `generalizability`: `generic`, `user_preference`, `project_case`, or `pending`;
- `anti_pattern`: the failure mode when known;
- `promotion_status`: `external_case`, `pending`, `approved_generic`, or `rejected`;
- optional opaque `case_ref`, which points to a project record outside the Skill package.

The top level contains only `schema_version`, `report_type`, `source`, and
`entries`; `source` contains only `kind` and optional `case_ref`. A
`project_case` source must provide a non-empty `source.case_ref`. Unknown
fields are rejected.

Concrete copy, timecodes, draft paths, track/material IDs, and media names stay
in the external case record. A generic rule enters the shared Skill only after
human approval and repeated evidence.
