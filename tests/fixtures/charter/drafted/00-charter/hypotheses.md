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

## H-001: Slotting rules are the bottleneck

```yaml
id: "H-001"        # permanent; next free number for this type, never reused
type: hypothesis
title: "Slotting rules are the bottleneck"
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
confirm_if: "Pick travel time is over 40% of order cycle time in the north DCs"            # evidence that would confirm it
reject_if: "Pick travel time is under 20% of order cycle time"             # evidence that would reject it
supported_by: []          # O/F-IDs
contradicted_by: []       # O/F-IDs
```

The warehouse slotting rules are the main cause of slow order-to-ship time.

## H-002: Carrier handoff waits dominate

```yaml
id: "H-002"        # permanent; next free number for this type, never reused
type: hypothesis
title: "Carrier handoff waits dominate"
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
question: "Q-002"              # Q-ID
confirm_if: "Orders wait more than four hours for pickup on average"            # evidence that would confirm it
reject_if: "Pickup waits are under one hour for most orders"             # evidence that would reject it
supported_by: []          # O/F-IDs
contradicted_by: []       # O/F-IDs
```

Waiting for carrier pickup is the largest single source of delay.
