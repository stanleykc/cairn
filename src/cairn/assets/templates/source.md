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
change_reason: ""         # one line: reason for the latest supersede or reject
change_trigger: ""        # new-evidence | client-feedback | rethinking
created: "YYYY-MM-DD"
material: ""              # document | meeting-transcript | meeting-notes
source_type: ""           # pdf | docx | markdown | text | vtt | srt | deck | spreadsheet | image | web | other (file format)
raw_file: ""              # path relative to 10-sources/raw/
raw_sha256: ""            # 64 hex characters, or "" for a restricted record
raw_bytes: 0              # size of the original, from stat
provided_by: ""
source_date: ""
meeting_title: ""         # meetings only
meeting_date: ""          # YYYY-MM-DD, required for meetings
attendees: []             # names, when known
author: ""                # required for meeting-notes
author_kind: ""           # person | ai-notetaker (required for meeting-notes)
extraction_status: in-progress  # in-progress | complete (complete only through finalize)
fidelity: pending         # pending | checked | unchecked | "" (restricted)
extraction_method: ""     # text | ocr | vision-description | mixed | none
derived: false            # true when content was derived (OCR, vision description), not read verbatim
restricted: false         # true when this source must not be sent to an external AI service
content_removed: false    # true only after restrict --remove-content
page_count: 0             # PDFs only
pages_reviewed: 0         # PDFs only, 0..page_count
uncertain_passages: []    # locators of passages whose extraction is uncertain
---

<!-- One file per source in 10-sources/extracted/. The original in 10-sources/raw/ is never modified. -->

## Context

The consultant's line of context, in their words: who provided it, when, why it matters,
how far to trust it.

## Description

*Written by `ingest`. Not part of the source.* Up to three sentences on what the source
is. No conclusions.

## Speakers

Transcripts only.

| Label | Confirmed name |
|---|---|

## Uncertain passages

One line per passage whose extraction is uncertain: `- <locator> — <why>`.

## Extracted content

<!-- cairn:content:start -->
<!-- cairn:content:end -->
