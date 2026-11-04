## D-###: <short title>

```yaml
id: "D-###"        # permanent; next free number for this type, never reused
type: decision
title: ""
status: proposed          # proposed | active | superseded | rejected
origin: ""                # client-document | interview-meeting | external-research | prior-engagement | llm-inference | consultant-note
confidence: ""            # high | medium | low
confidence_reason: ""     # one line
inference_confirmed: false  # consultant sets true after checking an llm-inference item against a source
audience: internal        # internal | client-ready (only the consultant sets client-ready)
supports: []              # IDs
contradicts: []           # IDs
derived_from: []          # IDs
supersedes: []            # IDs
clarifies: []             # IDs
change_reason: ""         # one line: reason for the latest supersede or reject
change_trigger: ""        # new-evidence | client-feedback | rethinking
created: "YYYY-MM-DD"
decides: []              # X/H-IDs
outcome: ""               # accepted | rejected | deferred
rationale: ""
decided_by: ""
decided_on: ""            # YYYY-MM-DD
```

What was decided and why, in a few sentences.
