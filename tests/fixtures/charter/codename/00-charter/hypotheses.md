---
type: collection
holds: hypothesis
---

# Hypotheses

Working hypotheses that answer the key questions. Add one entry per hypothesis, using the
block in `_templates/hypothesis.md`: a `## H-###: <short title>` heading, a fenced `yaml`
block with the fields, then free text. Use the next free number and never reuse one. Each
hypothesis links to the question it answers (`question: Q-###`). A rejected hypothesis
keeps its rationale and the evidence against it.

## H-001: Northwind discounts too deeply at quarter end

```yaml
id: "H-001"        # permanent; next free number for this type, never reused
type: hypothesis
title: "Northwind discounts too deeply at quarter end"
status: proposed          # proposed | active | superseded | rejected
origin: consultant-note   # client-document | interview-meeting | external-research | prior-engagement | llm-inference | consultant-note
confidence: low            # high | medium | low
confidence_reason: "Consultant hunch from prior fulfillment work"     # one line
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
question: "Q-001"              # Q-ID
confirm_if: "Quarter-end discounts exceed 15% on most large deals"            # evidence that would confirm it
reject_if: "Quarter-end discounts are in line with the rest of the quarter"             # evidence that would reject it
supported_by: []          # O/F-IDs
contradicted_by: []       # O/F-IDs
```

Northwind's quarter-end discounting gives away more margin than it wins in volume.
