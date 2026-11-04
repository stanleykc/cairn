---
type: collection
holds: assumption
---

# Assumptions

Assumptions the work relies on. Add one entry per assumption, using the block in
`_templates/assumption.md`: an `## A-###: <short title>` heading, a fenced `yaml` block
with the fields, then free text. Use the next free number and never reuse one. Record the
basis for each assumption and the questions it affects.

## A-001: Volumes stay near last year

```yaml
id: "A-001"        # permanent; next free number for this type, never reused
type: assumption
title: "Volumes stay near last year"
status: proposed          # proposed | active | superseded | rejected
origin: consultant-note   # client-document | interview-meeting | external-research | prior-engagement | llm-inference | consultant-note
confidence: medium            # high | medium | low
confidence_reason: "Consistent with what the client said at kickoff"     # one line
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
basis: "Client planning forecast, as summarized by the consultant"
questions: ["Q-001"]             # Q-IDs
```

Order volumes stay within 10% of last year through December. If they spike, the baseline measurements will not be comparable.

## A-002: DC staffing stays at current levels

```yaml
id: "A-002"        # permanent; next free number for this type, never reused
type: assumption
title: "DC staffing stays at current levels"
status: proposed          # proposed | active | superseded | rejected
origin: consultant-note   # client-document | interview-meeting | external-research | prior-engagement | llm-inference | consultant-note
confidence: medium            # high | medium | low
confidence_reason: "Consistent with what the client said at kickoff"     # one line
inference_confirmed: false  # consultant sets true after checking an llm-inference item against a source
audience: client-ready        # internal | client-ready (only the consultant sets client-ready)
supports: []              # IDs
contradicts: []           # IDs
derived_from: []          # IDs
supersedes: []            # IDs
clarifies: []             # IDs
change_reason: ""         # one line: reason for the latest supersede or reject
change_trigger: ""        # new-evidence | client-feedback | rethinking
created: "2026-11-03"
basis: "Hiring freeze mentioned by the sponsor"
questions: ["Q-003"]             # Q-IDs
```

Staffing in the north DCs stays at current levels during the engagement. If it changes, productivity comparisons need adjusting.

## A-003: Cites a source by mistake

```yaml
id: "A-003"        # permanent; next free number for this type, never reused
type: assumption
title: "Cites a source by mistake"
status: proposed          # proposed | active | superseded | rejected
origin: consultant-note   # client-document | interview-meeting | external-research | prior-engagement | llm-inference | consultant-note
confidence: medium            # high | medium | low
confidence_reason: "Consistent with what the client said at kickoff"     # one line
inference_confirmed: false  # consultant sets true after checking an llm-inference item against a source
audience: internal        # internal | client-ready (only the consultant sets client-ready)
supports: ["S-001"]              # IDs
contradicts: []           # IDs
derived_from: []          # IDs
supersedes: []            # IDs
clarifies: []             # IDs
change_reason: ""         # one line: reason for the latest supersede or reject
change_trigger: ""        # new-evidence | client-feedback | rethinking
created: "2026-11-03"
basis: "Hiring freeze mentioned by the sponsor"
questions: ["Q-003"]             # Q-IDs
```

Hand-written assumption that cites a source.
