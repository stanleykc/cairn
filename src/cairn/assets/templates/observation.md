---
id: "O-###"        # permanent; next free number for this type, never reused
type: observation
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
source: ""                # S-ID
locator: ""               # page, slide, table, timestamp or URL
questions: []             # Q-IDs
derived: false            # true when the claim was read from derived content (OCR, vision description)
---

One claim, from one source, with no interpretation.
