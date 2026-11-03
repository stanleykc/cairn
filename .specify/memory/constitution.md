# Cairn Constitution

Cairn (Curated Analysis, Insight and Recommendation Network) is a text-based framework that
turns the material of a consulting engagement into a traceable chain from cited evidence to
client recommendations. Agents collect, extract, connect and draft; the consultant decides
what is true, what matters and what the client sees.

## Core Principles

### I. Text-First: Files, Not a Platform

- An engagement MUST be a single folder of plain markdown files with YAML front matter,
  readable and editable in any editor (VS Code, Obsidian) and by any agent.
- Each skill MUST be a folder containing a `SKILL.md` plus any templates or scripts it needs.
  Skills are instructions first; scripts are permitted only where a deterministic check is
  more reliable than instructions (e.g., ID assignment, link validation, traceability checks).
- Scripts MUST read and write the same plain files and MUST NOT introduce a database,
  server, or proprietary format as the system of record.
- Status MUST live in front matter, not in folder location, so moving a file never changes
  its meaning.
- A dedicated platform (interface, database, multi-user access) MUST NOT be built until the
  file-based version has passed the phase gates and shown where it strains.

**Rationale:** Plain text keeps every object diffable, versionable and portable, and proves the
data model on real engagements before anything heavier is committed to.

### II. Originals Are Immutable

- Nothing in `10-sources/raw/` may be modified, renamed, re-encoded or deleted by any skill.
- All work MUST happen on the extracted markdown in `10-sources/extracted/` (one file per
  source, `S-###`).
- Every extracted source MUST record its extraction method (text, OCR, vision description)
  and MUST flag any passage whose extraction is uncertain.

**Rationale:** The original is the final arbiter of every citation; if it changes, no evidence
trail can be trusted.

### III. Atomic, Cited Evidence

- The observation is the smallest unit of work: one claim, from one source, with no
  interpretation. Interpretation belongs in findings.
- Every claim written by a skill MUST cite a source ID and a locator (page, slide, table,
  timestamp or URL).
- Every finding, issue, opportunity, option and recommendation MUST link down to the
  observations that support it, and MUST list contradicting observations where they exist.
- A claim without a citation MUST NOT be promoted to active.
- In this principle, a *claim* is an evidence claim: an observation, or anything built on
  observations (findings, issues, opportunities, options, recommendations). Charter framing
  items (questions, hypotheses, assumptions) assert nothing about the sources. They are
  recorded with origin *consultant note* or *LLM inference*, cite no source, and may become
  active on the consultant's approval. Later skills link them to evidence.

**Rationale:** Traceability is built in by construction, not reconstructed afterwards. Any
conclusion can be checked against its evidence.

### IV. Visible Provenance and Inference

- Every object MUST carry `origin` (client document, interview/meeting, external research,
  prior engagement, LLM inference, consultant note/suggestion) and `confidence`
  (high/medium/low, with a one-line reason).
- Anything the model inferred rather than read MUST be marked with origin *LLM inference*.
- Content derived rather than read verbatim (OCR text, vision descriptions of charts,
  diagrams and whiteboard photos) MUST be flagged as derived.
- An item with origin *LLM inference* MUST NOT become client-ready until the consultant
  confirms it against a source.

**Rationale:** The consultant and the client must always be able to tell what a source said
from what a model concluded.

### V. Stable IDs, Link by ID

- Every object MUST have a short, permanent ID with a type prefix (e.g., `S-011`, `O-042`,
  `F-007`, `Q-003`, `H-004`, `X-012`, `D-002`, `L-005`).
- New IDs MUST be assigned from the next free number for that type. IDs MUST NOT be reused,
  even after an object is superseded or rejected.
- Links between objects MUST use IDs only, never file paths or titles, so files can be
  renamed or moved without breaking links.
- Findings, issues, opportunities and options MUST be one object per file. Observations
  SHOULD be one per file; grouping per source is permitted only for high-volume sources.

**Rationale:** Permanent IDs make the evidence graph robust to reorganization and make every
object independently versionable and linkable.

### VI. Never Delete, Supersede

- Objects MUST NOT be deleted or overwritten to change their claim. A changed idea MUST be
  recorded as `superseded` or `rejected`, with a reason and a trigger (new evidence, client
  feedback, rethinking).
- Clarifications (*clarifies*) refine an object without changing its claim; corrections
  (*supersedes*) replace a wrong claim, record what was wrong, and MUST flag every object
  built on it for review.
- Every supersede, clarify and correct event MUST be recorded in `60-log/changelog.md` with
  a date.
- Rejected options and hypotheses MUST keep their rationale and the evidence against them, so
  later skills can check new proposals against these negative lessons.

**Rationale:** The history of thinking is an asset. Keeping it prevents repeated mistakes and
powers the what-changed report.

### VII. Agents Propose, the Consultant Decides (NON-NEGOTIABLE)

- Skills MUST write new objects with status `proposed`, using the templates in `_templates/`,
  and to `_inbox/` wherever the pipeline routes output through triage.
- Only the consultant may set an object to `active`, accept or reject an option, or mark
  anything `client-ready`. No skill may set `audience: client-ready`.
- Client views and deliverables MUST be generated only from items that are `active` and
  `client-ready`; no deliverable is written separately from the underlying model.
- Content written by hand by the consultant or analyst counts fully, the same as agent output,
  and is subject to the same citation and provenance rules.

**Rationale:** The framework assists the consultant's judgment and does not replace it. Every
promotion and every release to the client is an explicit human decision.

### VIII. Confidentiality and the Anonymization Boundary (NON-NEGOTIABLE)

Lessons flow across engagements; client data does not. The boundary between the two is a
deliberate anonymization step.

- **Within an engagement**, everything — including client names and raw sources — MUST stay
  inside the engagement folder.
- **Across engagements**, only lessons and option patterns may be shared, and only after being
  rewritten to remove client names, figures and identifying details. The consultant MUST
  approve each lesson before it leaves the engagement.
- **Model use.** The charter MUST record what the client agreement allows to be sent to
  external AI services. `ingest` MUST refuse any source marked restricted, and the rest of the
  engagement MUST be able to proceed without it.
- **Retention.** At close, raw sources MUST follow the client agreement (returned, archived or
  deleted); anonymized lessons are kept in the firm library.
- The Cairn framework repository itself MUST NOT contain real client data. Examples, fixtures
  and test engagements MUST be synthetic or anonymized.

**Rationale:** Client trust and contractual obligations outrank convenience. Reuse of
knowledge is valuable only if it never leaks the client it came from.

## Skill Contract

Every skill MUST comply with the following rules. A skill that cannot comply MUST stop and
report why rather than produce non-compliant output.

### Rules every skill follows

1. Never modify anything in `10-sources/raw/`.
2. Cite every evidence claim with a source ID and a locator (page, slide, timestamp, URL).
3. Mark anything the model inferred, rather than read, as origin *LLM inference*.
4. Write new objects as *proposed*, to `_inbox/` where the pipeline shows it, using the
   templates in `_templates/`.
5. Assign IDs from the next free number for that type, and link by ID only.
6. Never mark an item client-ready; only the consultant does that.

### Skill-specific requirements

- **ingest** carries most of the format risk. Charts, diagrams and photos of whiteboards MUST
  get both OCR text and a written description, each flagged as derived. Spreadsheets MUST keep
  tables as markdown tables, not prose. Transcripts SHOULD be split by speaker. Sources marked
  restricted MUST be refused.
- **extract-observations** MUST stay atomic: one claim per observation, no interpretation.
- **synthesize** MUST state the "so what" of each finding in one sentence and MUST list every
  supporting and contradicting observation.
- **find-prior-art** MAY wrap the firm's existing OCI library skills (find prior art, ask the
  library) rather than reimplementing them, provided client-identifying details are removed
  from anything written back into an engagement or the firm library.
- **draft-deliverable** MUST draw only on `active`, `client-ready` items.
- **check-traceability** MUST report broken links, orphan claims and unconfirmed LLM
  inferences in any draft it checks.

### Canonical engagement layout

Skills MUST read and write the engagement folder layout defined in the framework design:
`_inbox/`, `_templates/`, `00-charter/`, `10-sources/{raw,extracted}/`, `20-research/`,
`30-observations/`, `40-synthesis/{findings,issues,opportunities}/`, `50-options/`,
`60-log/`, `70-views/`, `80-deliverables/`. Changing this layout is a constitution amendment.

## Development Workflow and Quality Gates

- **Spec-driven.** Each skill or framework change is specified with Spec Kit before it is
  built. Every plan MUST pass a Constitution Check against Principles I–VIII and the Skill
  Contract; any deviation MUST be justified in the plan's complexity tracking.
- **Minimal and focused.** Changes SHOULD be the smallest that deliver the specified
  behavior. Templates, front-matter fields and skill instructions are kept consistent with
  one another; a change to the data model MUST update every template and skill that uses it.
- **Validation on known outcomes.** Skills MUST be validated on a completed engagement whose
  outcome is already known, using an anonymized or locally held copy that never enters this
  repository (Principle VIII).
- **Phased build.**
  - Phase 1 (core loop): `charter`, `ingest`, `extract-observations`, `triage`,
    `synthesize`, `what-changed`.
  - **Gate 1:** the core loop rebuilds the past engagement's key findings, each with a working
    evidence trail, and the data model needs no major change.
  - Phase 2: research, prior art, hypothesis testing, contradictions, change recording,
    debrief.
  - **Gate 2:** on a live engagement, triage and synthesis take less time than the current
    approach, and the what-changed report is used for client updates.
  - Phase 3: options, challenge, deliverable drafting, traceability checking. After Phase 3,
    decide whether a dedicated platform is warranted (Principle I).
- **Review.** Every skill change MUST be reviewed against the Skill Contract before merge,
  including a check that sample output carries citations (for evidence claims), provenance,
  `proposed` status and ID-only links.

## Governance

- This constitution supersedes other project practices. Where a design note, template or
  skill conflicts with it, the constitution wins until it is amended.
- **Amendments** MUST be proposed as a change to `.specify/memory/constitution.md` that states
  the reason, the version bump, and the templates or skills affected. The project owner
  approves each amendment; dependent templates and skills are brought into line in the same
  change or tracked as follow-up tasks.
- **Versioning** follows semantic versioning:
  - MAJOR: removal or backward-incompatible redefinition of a principle or Skill Contract rule.
  - MINOR: a new principle or section, or materially expanded guidance.
  - PATCH: clarifications, wording and typo fixes with no change in meaning.
- **Compliance review.** Every spec, plan and pull request MUST be checked against this
  constitution. Principles marked NON-NEGOTIABLE (VII and VIII) cannot be waived by
  complexity justification; they change only by amendment.
- The full framework design (data model, pipeline, skill catalogue, analyst workflow) is the
  runtime guidance for applying these principles; it is maintained alongside this document.

**Version**: 1.0.1 | **Ratified**: 2026-11-03 | **Last Amended**: 2026-11-03
