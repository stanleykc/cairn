---
id: "acme-fulfillment-review"
type: engagement
engagement_name: "Fulfillment Review"
client: "Acme"
client_code_name: ""
lead_consultant: "Test Lead"
team: []
start_date: 2026-11-03
created: 2026-11-03
framework_version: "0.2.0"  # updated only by cairn refresh
model_use: unconfirmed  # allowed | restricted | unconfirmed
model_use_notes: ""  # specific restrictions, free text
---

# Engagement record

This file is the authoritative record of the engagement's identity and settings. Skills
read it; edit the values above by hand when they change.

- `id`: the folder name. It never changes after the engagement is created.
- `type`: always `engagement`. Tools use it to recognize an engagement folder.
- `engagement_name`: the engagement's name, as typed.
- `client`: the client's real name. It may be empty when a code name is used, and it
  appears in no other generated file.
- `client_code_name`: the code name used in folder names and documents instead of the
  client's name. Empty when no code name is used.
- `lead_consultant`: the consultant who leads the engagement.
- `team`: the analysts working on the engagement.
- `start_date`: the date the engagement started.
- `created`: the date this folder was created.
- `framework_version`: the Cairn framework version that provided the templates and skills.
  Only `cairn refresh` changes it.
- `model_use`: what the client agreement allows to be sent to external AI services:
  `allowed`, `restricted` (some sources must not be sent; mark them `restricted: true`) or
  `unconfirmed` (not known yet: ask before sending anything).
- `model_use_notes`: what may or may not be sent, in the consultant's words. `""` when
  none is recorded.

**Confirm `model_use` before any source is ingested.** The copy in `00-charter/scope.md` is
for reading; this file is the authoritative copy.
