---
id: ${id_q}
type: engagement
engagement_name: ${engagement_name_q}
client: ${client_q}
client_code_name: ${client_code_name_q}
lead_consultant: ${lead_consultant_q}
team: ${team_json}
start_date: ${start_date}
created: ${created}
framework_version: ${framework_version_q}  # updated only by cairn refresh
model_use: ${model_use}  # allowed | restricted | unconfirmed
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
