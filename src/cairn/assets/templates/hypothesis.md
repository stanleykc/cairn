## H-###: <short title>

```yaml
id: "H-###"        # permanent; next free number for this type, never reused
type: hypothesis
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
created: "YYYY-MM-DD"
question: ""              # Q-ID
supported_by: []          # O/F-IDs
contradicted_by: []       # O/F-IDs
```

The working hypothesis in one sentence, and what evidence would confirm or reject it.
