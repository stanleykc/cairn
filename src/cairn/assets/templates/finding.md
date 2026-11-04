---
id: "F-###"        # permanent; next free number for this type, never reused
type: finding
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
so_what: ""               # one sentence
supported_by: []          # O-IDs
contradicted_by: []       # O-IDs
questions: []             # Q-IDs
---

## So what

The implication for the client, in one sentence.

## Evidence

The supporting observations, by ID, and how they fit together.

## Contradicting evidence

Observations that point the other way, by ID. Write "None found" if there are none.
