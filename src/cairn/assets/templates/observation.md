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
change_reason: ""         # one line: reason for the latest supersede or reject
change_trigger: ""        # new-evidence | client-feedback | rethinking
created: "YYYY-MM-DD"
source: ""                # S-ID
locator: ""               # page, heading path, ¶, timestamp/turn; tables: "<unit> › table n › row m"
questions: []             # Q-IDs
derived: false            # true when the claim was read from derived content (OCR, vision description)
speaker: ""               # transcripts only: confirmed name, else the original label
passage_kind: ""          # text | table-row | comment | tracked-change
translated: false         # true when the claim is an English rendering of a non-English passage
---

## Claim

One claim, from one source, with no interpretation.

## Passage

> The exact words from the source at the locator.
