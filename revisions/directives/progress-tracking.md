# progress-tracking.md
**Directive: PROGRESS.md Governance**

Copy this file as-is to any project. It does not contain project-specific content.
It is not modified by `/init`.

11-layer coverage: Layers 1–6 (maturity assessment), Layer 8 (failure recovery)

---

## Purpose

`PROGRESS.md` is the authoritative repository development ledger. It tracks capability maturity against the intended deliverable, preserves continuity across sessions, and prevents regression and duplicate work.

Progress means **capability maturity across the 11-layer framework** — not code presence.

---

## Session Startup Rule

At the start of any work session, Claude must:

1. Read `CLAUDE.md`
2. Read `AGENTS.md`
3. Read `PROGRESS.md`
4. Read the Layer Artifacts table in `CLAUDE.md` and navigate to relevant layer files for the current task
5. Determine:
   - what the system is intended to deliver
   - which capabilities are required, partial, or missing
   - the current maturity of each relevant capability across the 11 layers
   - the next highest-value implementation task

All new work must align with the intended deliverable and the documented repository state.

---

## Creation Rule

If `PROGRESS.md` does not exist, create it before any substantial implementation work. This is a one-time bootstrapping action — never overwrite or reset an existing `PROGRESS.md`.

The initial version must include:
- project overview
- current repository phase
- known architecture
- implementation status by capability
- outstanding gaps
- testing status
- next recommended actions
- deliverable alignment summary against the requirements artifact (Layer 1)

---

## Mandatory Update Conditions

Update `PROGRESS.md` whenever:

- new features are implemented
- tests are added or modified
- directives materially change
- integrations are completed
- bugs are resolved
- architecture or schemas change
- phases advance
- major refactors occur
- production risks are identified
- capability maturity materially changes
- a deliverable gap is closed, opened, or reclassified

No meaningful repository change is complete until `PROGRESS.md` is updated.

---

## Capability Maturity Classification

Assess each relevant layer for each capability as one of:

| Classification | Meaning |
|---|---|
| Absent | No artifact or evidence exists |
| Planned | Intention documented, not yet built |
| Scaffolded | Structure exists, logic incomplete |
| Partially Implemented | Core logic present, gaps remain |
| Integrated | Connected to the system, runs end-to-end |
| Tested | Automated tests cover the behavior |
| Verified | Tests pass, behavior confirmed against directives |
| Production Ready | Stable, safe to run in production |

A capability is only as mature as its weakest required layer.

---

## Required Entry Structure

Each progress entry must contain:

**Header**
- Phase or milestone identifier
- Date
- Repository status classification

**Capability / Deliverable Alignment**
- Capability name and deliverable relevance (required / deferred / optional)
- Current maturity classification
- 11-layer coverage: which layers are present, which are missing

**What Changed**
- Files created or modified
- Architectural or behavioral changes
- New integrations

**Validation**
- Tests added or updated
- Verification steps performed
- Known unverified areas

**Risks / Limitations**
- Deferred work, technical debt, known instability
- Placeholder implementations

**Next Actions**
- Recommended next steps
- Remaining blockers
- Required approvals if applicable

---

## Preferred Capability Reporting Format

```
Capability:           <name>
Deliverable status:   Required / Deferred / Optional
Requirements:         Defined / Partial / Absent
Specs:                Defined / Partial / Absent
Directives:           Present / Partial / Absent
Execution Plan:       Implemented / Partial / Absent
State Model:          Defined / Partial / Absent
Test Scenarios:       Covered / Partial / Absent
System Loop:          Integrated / Partial / Absent
Failure Playbook:     Defined / Partial / Absent
Environment Model:    Safe / Shadow-only / Absent
Data Lifecycle:       Defined / Partial / Absent
Evolution Strategy:   Defined / Not yet formalized
Overall maturity:     <classification>
Remaining gaps:       <list>
Next step:            <one action>
```

---

## Anti-Drift Rule

Claude must not:
- jump to low-priority enhancements before core deliverable gaps are closed
- treat partial implementation as equivalent to deliverable completion
- optimize or polish a capability whose core maturity gaps are still unresolved
- invent roadmap items not grounded in the Layer 1 requirements artifact

Prefer closing the highest-value maturity gap in a required capability over adding unrelated features.

---

## Gap Analysis Rule

If the requirements artifact, the codebase, and `PROGRESS.md` disagree, Claude must not guess.

Claude must:
1. Identify the discrepancy
2. Inspect the relevant repository evidence
3. Document the discrepancy in `PROGRESS.md`
4. Choose the safest next step based on verified evidence

---

## Failure Recovery Rule

When failures occur, document in `PROGRESS.md`:
- root cause
- affected components
- corrective actions taken
- tests added
- prevention strategy
- remaining risks
- impact on capability maturity
- whether the failure exposed a missing layer

Failures are repository learning events.

---

## Definition of Done

A task is complete only when:

- implementation exists and non-trivial logic has unit tests
- behavior-changing logic updates the relevant directive
- end-to-end impact is verified where applicable
- no secrets are introduced
- `PROGRESS.md` reflects the updated capability maturity
- a junior developer could understand what changed and why

A capability is complete only to the maturity level supported by evidence across the relevant 11 layers — not by code presence alone.
