# Three-skill workflow state

The skills share these handoff states:

| State | Allowed values | Owner | Meaning |
|---|---|---|---|
| `content_pass` | `draft`, `stable`, `approved` | `jianying-rough-cut` | the semantic rough-cut decisions and plan are at the stated review level; `jianying-editor` owns project execution |
| `subtitle_alignment` | `not_started`, `draft`, `stable`, `approved` | `jianying-rough-cut` | current visible subtitles or generated timed-transcript units have been checked against edited audio |
| `packaging_staging` | `pending`, `reviewing`, `approved` | `jianying-packaging` | upper-track emphasis candidates have been reviewed |
| `packaging_apply` | `dry_run`, `applied`, `verified` | `jianying-editor` | the approved package was prepared, written, and independently read back |
| `visual_audio_review` | `pending`, `passed`, `needs_revision` | human/editorial review | the reopened Jianying result matches the intended visible and audible result |

`jianying-rough-cut` owns editorial decisions and plan status only. `jianying-editor` owns project probing, timeline reads/writes, cloning, and execution of approved ranges. A `content_pass` value never by itself means that project execution occurred.

The normal gate is:

```text
content_pass stable/approved
→ subtitle_alignment approved
→ packaging_staging reviewing/approved
→ packaging_apply dry_run/applied/verified
→ visual_audio_review passed
```

If packaging discovers a semantic problem, set the packaging result to `needs_rough_cut_review` and return to the content owner. Do not silently consume the issue as a display-only change.
