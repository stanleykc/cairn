---
type: collection
holds: question
---

# Questions

The key questions the engagement must answer. Add one entry per question, using the block
in `_templates/question.md`: a `## Q-###: <short title>` heading, a fenced `yaml` block
with the fields, then free text. Use the next free number and never reuse one. Each
question can list the hypotheses that answer it.

## Q-001: Where is Northwind leaving margin on the table

```yaml
id: "Q-001"        # permanent; next free number for this type, never reused
type: question
title: "Where is Northwind leaving margin on the table"
status: proposed          # proposed | active | superseded | rejected
origin: consultant-note   # client-document | interview-meeting | external-research | prior-engagement | llm-inference | consultant-note
confidence: medium            # high | medium | low
confidence_reason: "Raised by the sponsor at kickoff"     # one line
inference_confirmed: false  # consultant sets true after checking an llm-inference item against a source
audience: internal        # internal | client-ready (only the consultant sets client-ready)
supports: []              # IDs
contradicts: []           # IDs
derived_from: []          # IDs
supersedes: []            # IDs
clarifies: []             # IDs
change_reason: ""         # one line: reason for the latest supersede or reject
change_trigger: ""        # new-evidence | client-feedback | rethinking
created: "2026-11-03"
priority: high            # high | medium | low
raised_by: "Test Lead"
hypotheses: ["H-001"]            # H-IDs
```

Where is Northwind's current pricing leaving margin on the table? It sets the focus of the study.
