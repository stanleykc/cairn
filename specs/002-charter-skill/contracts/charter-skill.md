# Contract: `charter` skill

The interface the consultant uses, and the guarantees later skills can rely on. The
skill's file is `src/cairn/assets/skills/charter/SKILL.md`. It is copied to
`<engagement>/.claude/skills/charter/` by `cairn init` and `cairn refresh`.

## Invocation

| Form | Example |
|---|---|
| Slash command, no input | `/charter` |
| Slash command with up-front input (FR-011) | `/charter Objectives: cut order-to-ship time 30%. Final readout 2026-12-04. Hunch: the WMS slotting rules are the bottleneck.` |
| Natural language (model-invoked) | "Let's set up the charter", "I need to revise the hypotheses after today's steer" |

It must be run from inside an engagement folder or one of its subfolders. Otherwise it
stops with the script's "Not inside a Cairn engagement…" message (FR-002).

## Front matter

See research R21: `name: charter`, a one-paragraph `description`, `argument-hint`, and
`allowed-tools: Read, Edit, Write, Bash(python3 *charter.py *)`.

## Files

~~~text
charter/
├── SKILL.md                     # flow, rules, never-do list (target ≤ 250 lines)
├── reference/
│   ├── interview.md             # topic-by-topic prompts, confirm-don't-re-ask, starter lenses
│   ├── review-and-revise.md     # one-screen summary, approve/reject/edit, new version, relink, clarify
│   ├── change-convention.md     # FR-030 shared convention (byte-identical to the contract)
│   └── formats.md               # filled examples: Q/H/A entries, scope sections, rows, bullets, changelog lines
└── scripts/
    └── charter.py               # see charter-script.md
~~~

## Session flow

~~~text
status ─┬─ exit 2 ──────────────────────────────▶ stop, explain cairn init         (FR-002)
        └─ ok
            ▼
   model_use == unconfirmed? ── ask; consultant may decline ──▶ model-use --set    (FR-004/005)
   model_use in {restricted, unconfirmed}? ── remind once: don't paste client text  (FR-007)
            ▼
   charter_state == empty ──▶ INTERVIEW (topics in order, confirm what's known,
                              save each confirmed topic, run check)                 (FR-008–022)
   charter_state != empty ──▶ REVISION (summarize, ask what changed; offer
                              to finish missing topics)                             (FR-003, FR-023–029)
            ▼
   GAP CHECK + ≤ 5 suggestions, each kept or discarded                              (FR-031/032)
            ▼
   REVIEW: one-screen summary; apply approve / reject / edit / approve-all          (FR-033–036)
            ▼
   END SUMMARY                                                                       (FR-039)
~~~

The consultant can stop at any point. Everything confirmed so far is already saved
(FR-022), and the end summary is still shown, listing the topics not yet covered (US1-6).

## Outputs

| File | What the skill may do |
|---|---|
| `00-charter/scope.md` | Fill or replace sections, add missing headings or front matter fields, set `charter_status`, `approved_on`, `approved_by`. The Model use section is changed only through `charter.py model-use`. |
| `00-charter/questions.md`, `hypotheses.md`, `assumptions.md` | Append entries. Change `status`, `change_reason`, `change_trigger` and link fields on consultant instruction. Clarify wording in place. Amend in place only entries created in this session. |
| `00-charter/stakeholders.md` | Append rows. Change a row on instruction. |
| `00-charter/lenses.md` | Append bullets. Change a bullet on instruction. |
| `60-log/changelog.md` | Append events ([change-convention.md](change-convention.md)) |
| `engagement.md` | Only `model_use` and `model_use_notes`, only through `charter.py model-use` |

## Never

The first section of `SKILL.md` lists these as hard rules:

1. Never open, list, search or read anything in `10-sources/`, or any document the
   consultant offers. Decline, and ask for a summary instead (FR-006).
2. Never read `engagement.md`. Use `charter.py status` (R7).
3. Never delete an entry, row or bullet, and never change an existing item's claim in place
   (FR-021).
4. Never set `active`, `rejected` or `superseded` without the consultant's explicit
   instruction in this session (FR-034).
5. Never set `audience: client-ready` or `inference_confirmed: true` (FR-036).
6. Never cite a source ID or write `origin: client-document` (FR-019).
7. Never write the real client name when a code name is in use (FR-037).
8. Never use web search, fetch tools, or prior-art and library skills during `charter`
   (FR-038).
9. Never write a hypothesis without a question, or a revision without a reason and a
   trigger (FR-015, FR-023).

## End summary (FR-039)

Shown at the end of every session, including one that stops early:

~~~text
Charter — <engagement_name> (<client_label>) · state: draft|approved [on <date> by <name>]
Model use: <value>[ — <notes>]   ⚠ settle before ingesting any source   (when unconfirmed)

Written:   Q-001, Q-002, H-001, A-001 · scope: Objectives, Timeline · 3 stakeholders · 4 lenses
Changed:   H-002 → H-004 (pending approval) · A-001 rejected · scope/Timeline
Not covered: Constraints, Evaluation criteria
Review these (they link to changed items): O-014 (questions), F-003 (questions)
Gaps:      Q-002 has no hypothesis · Deliverable "Board deck" has no date

Next: review and approve the charter · add originals to 10-sources/raw/ · run ingest
~~~

## Guarantees for later skills

- Every `Q`, `H` and `A` entry passes `charter.py check` when a session ends. If it
  doesn't, the skill reports the remaining problems in the summary and doesn't hide them.
- `H.question` ↔ `Q.hypotheses` agree in both directions.
- `confirm_if` and `reject_if` are present on every hypothesis the skill writes. They may be
  empty only if the consultant declined, and that is reported as a gap.
- `lenses.md` names can be used as lens names in later requests.
- Every supersede, clarify, reject, scope change and relink has a changelog event.
