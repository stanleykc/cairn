## L-###: <short title>

```yaml
id: "L-###"        # permanent; next free number for this type, never reused
type: lesson
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
polarity: ""              # positive | negative
learned_from: []          # D/X/H-IDs
anonymized: false
share_approved: false     # consultant approval required before a lesson leaves the engagement
```

The lesson in one or two sentences. Before sharing it outside the engagement, rewrite it
to remove client names, figures and identifying details.
