---
id: "S-###"        # permanent; next free number for this type, never reused
type: source
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
source_type: ""           # pdf | deck | spreadsheet | image | transcript | web | other
raw_file: ""              # file name in 10-sources/raw/
provided_by: ""
source_date: ""
extraction_method: ""     # text | ocr | vision-description | mixed
derived: false            # true when content was derived (OCR, vision description), not read verbatim
restricted: false         # true when this source must not be sent to an external AI service
uncertain_passages: []    # locators of passages whose extraction is uncertain
---

<!-- One file per source in 10-sources/extracted/. The original in 10-sources/raw/ is never modified. -->

## Summary

What this source is and why it matters to the engagement.

## Extracted content

The extracted text. Keep tables as markdown tables. Mark derived content (OCR, vision
descriptions of charts, diagrams and photos) as derived.

## Uncertain passages

One line per passage whose extraction is uncertain, with its locator.
