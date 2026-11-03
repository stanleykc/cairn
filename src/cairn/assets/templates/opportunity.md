---
id: "P-###"        # permanent; next free number for this type, never reused
type: opportunity
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
supported_by: []          # F-IDs
contradicted_by: []       # F-IDs
---

## Opportunity

The advantage to exploit, in one or two sentences.

## Evidence

The findings that support it, by ID.

## Contradicting evidence

Findings that point the other way, by ID. Write "None found" if there are none.
