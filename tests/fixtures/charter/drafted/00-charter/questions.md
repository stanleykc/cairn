---
type: collection
holds: question
---

# Questions

The key questions the engagement must answer. Add one entry per question, using the block
in `_templates/question.md`: a `## Q-###: <short title>` heading, a fenced `yaml` block
with the fields, then free text. Use the next free number and never reuse one. Each
question can list the hypotheses that answer it.

## Q-001: Why is order-to-ship slow in the north DCs

```yaml
id: "Q-001"        # permanent; next free number for this type, never reused
type: question
title: "Why is order-to-ship slow in the north DCs"
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

Why is order-to-ship time in the north DCs above target? The sponsor's main objective depends on it.

## Q-002: Which steps drive most of the delay

```yaml
id: "Q-002"        # permanent; next free number for this type, never reused
type: question
title: "Which steps drive most of the delay"
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
hypotheses: ["H-002"]            # H-IDs
```

Which steps between order release and carrier handoff account for most of the delay? This tells us where to focus.

## Q-003: What operating model fits without new headcount

```yaml
id: "Q-003"        # permanent; next free number for this type, never reused
type: question
title: "What operating model fits without new headcount"
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
priority: medium            # high | medium | low
raised_by: "Test Lead"
hypotheses: []            # H-IDs
```

What fulfillment operating model could the client run without adding headcount? It shapes the final recommendations.
