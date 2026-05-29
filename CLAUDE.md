# CLAUDE.md  
**Colaberry Agent Project Rules, QA Model & Operating Contract**

This file defines how Claude (and other AI coding agents) must behave when working in this repository.

This project does **not** use Moltbot.  
Claude Code and other coding agents are used to **design, build, validate, and maintain** the system — they are **not the runtime system itself**.

---

## Core Principle

LLMs are probabilistic.  
Production systems must be deterministic.

Claude’s role is to:
- reason
- plan
- orchestrate
- validate
- modify instructions and code **carefully and audibly**

Claude is **never** the runtime executor of business logic, tests, or workflows.

---

## High-Level Architecture

This project follows an **Agent-First, Deterministic-Execution** model with **Test-First Validation**.

---

## System Layers

### Layer 1 — Directives (What to do)
- Human-readable SOPs
- Stored in `/directives`
- Written in plain language
- Describe:
  - goals
  - inputs
  - outputs
  - edge cases
  - safety constraints
  - verification expectations

Directives are **living documents** and must be updated as the system learns.

---

### Layer 2 — Orchestration (Decision making)
- This is **Claude**
- Responsibilities:
  - read relevant directives
  - plan changes
  - design tests before logic
  - decide which tools, scripts, and tests are required
  - ask clarifying questions when intent is ambiguous
  - update directives with learnings

Claude **never** executes business logic or tests directly.

---

### Layer 3 — Execution (Doing the work)
- Deterministic scripts
- Stored in `/execution` and optionally `/services/worker`
- Responsibilities:
  - API calls
  - data processing
  - database reads/writes
  - file operations
  - scheduled jobs

Execution code must be:
- repeatable
- testable
- auditable
- safe to rerun

---

### Layer 4 — Verification (Proving it works)
- Stored in `/tests`
- Includes:
  - unit tests
  - integration tests
  - end-to-end tests
  - UI and workflow validation
- Tests are **first-class citizens**, not afterthoughts

Claude designs tests; tools execute them.

---

## Folder Responsibilities

Claude must respect the following boundaries.

### `/agents`
- Agent personas and role definitions
- Behavioral descriptions
- No executable logic

---

### `/directives`
- SOPs and runbooks
- Step-by-step instructions
- Human-readable
- Must define *how success is verified*

---

### `/execution`
- Deterministic tools and scripts
- One script = one clear responsibility
- Core logic must be importable and testable
- No orchestration logic
- No prompts

---

### `/services/worker` (if present)
- Long-running or scheduled jobs
- Calls scripts from `/execution`
- Represents the **actual runtime system**

---

### `/tests`
- Automated verification layer
- Mirrors execution and worker structure
- May include:
  - unit tests
  - integration tests
  - Playwright / browser-based tests
  - API contract tests
  - visual regression tests

---

### `/config`
- Environment wiring (dev vs prod identifiers)
- No secrets

---

### `/tmp`
- Scratch space
- Always safe to delete
- Never committed

---

## Testing & Validation Rules (Non-Negotiable)

Testing is **mandatory** and **gated**.

---

### Unit Testing
- All non-trivial execution logic must have unit tests
- Pure logic tested without I/O
- External dependencies mocked
- Tests must:
  - be fast
  - be deterministic
  - run locally

---

### Integration Testing
- May touch:
  - dev sandboxes
  - test databases
  - mock APIs
- Must:
  - never touch production
  - require explicit opt-in (env flag or CI label)

---

### End-to-End & UI Testing
- Used to validate:
  - routing
  - links
  - forms
  - auth flows
  - permissions
  - UI state
- Browser automation tools (e.g., Playwright) are preferred
- Claude may:
  - generate crawl tests
  - define form test matrices
  - design visual regression rules
- Claude must **not** manually simulate UI behavior in prose

---

### Worker Testing
- Workers are tested as routing logic:
  - correct script selection
  - retry behavior
  - idempotency
  - error handling
- Workers must never send real communications during tests

---

### Directive Validation
Directives are validated for:
- required sections
- referenced files/scripts existence
- markdown integrity
- clarity for junior developers

---

## Claude Operating Rules

### 1. Never act blindly
- Always read relevant directives first
- If none exist, ask before creating one

---

### 2. Never mix layers
- No business logic in directives
- No orchestration logic in execution scripts
- No execution or testing inside Claude responses

---

### 3. Prefer deterministic verification
If behavior can be tested via code, **do not validate it narratively**.

---

### 4. Approval-gated changes
Claude must request approval before:
- large refactors
- schema changes
- deleting files
- production-impacting logic
- modifying safety, compliance, or testing baselines

---

### 5. Self-Annealing Loop (Mandatory)

When something fails:
1. Identify the root cause
2. Fix the script or logic
3. Add or update tests
4. Update the relevant directive
5. Confirm the system is stronger

Failures are inputs, not mistakes.

---

## Tooling Assumptions

Claude may assume:
- Claude Code is available
- VS Code / VSCodium / Cursor may be used
- Git is present
- CI runs automated tests

Claude must **not** assume:
- Moltbot exists
- proprietary automation platforms exist
- production credentials exist locally

---

## Intern Safety Rules

This repository may be worked on by interns.

Therefore:
- No destructive scripts without confirmation
- No production writes without explicit environment checks
- No secrets in repo
- Clear setup docs must exist
- One-command test execution must exist

Claude should optimize for:
- clarity
- reproducibility
- teachability

---

## Progress Tracking & Repository State Governance

### Mandatory Repository State File

This repository must maintain a root-level file named:

`PROGRESS.md`

`PROGRESS.md` is the authoritative repository development ledger and operational memory layer.

Its purpose is to:

* track implementation phases
* document architectural evolution
* record validation and testing evidence
* preserve cross-session continuity
* prevent regression and duplicate work
* expose incomplete or placeholder implementations
* provide auditable repository state history
* communicate current system maturity to humans and agents

---

## Creation Rule (Mandatory)

If `PROGRESS.md` does not exist:

Claude must create it before performing substantial implementation work.

The initial version must include:

* project overview
* current repository phase
* known architecture
* implementation status summary
* outstanding gaps
* testing status
* next recommended actions

No major repository work should proceed without a repository state tracking file.

---

## Session Startup Rule

At the start of any repository work session, Claude must:

1. Read `PROGRESS.md`
2. Determine:

   * current project phase
   * completed milestones
   * incomplete work
   * deferred items
   * architectural constraints
   * known risks
3. Align all new work with the documented repository state

Claude must treat `PROGRESS.md` as the primary continuity artifact between sessions.

---

## Mandatory Update Conditions

Claude must update `PROGRESS.md` whenever any of the following occur:

* new features are implemented
* tests are added or modified
* directives materially change
* integrations are completed
* bugs are resolved
* architecture changes
* schemas change
* phases advance
* major refactors occur
* edge cases are resolved
* production risks are identified
* validation baselines change

No meaningful repository change is considered complete until `PROGRESS.md` is updated.

---

## Required Entry Structure

Each progress entry must contain:

### Header

* Phase or milestone identifier
* Date/time
* Repository status classification

### What Changed

* Files created
* Files modified
* Architectural changes
* New integrations
* Behavioral changes

### Validation

* Tests added or updated
* Verification steps performed
* Deterministic validation evidence
* Integration validation status
* Known unverified areas

### Risks / Limitations

* Deferred work
* Technical debt
* Incomplete integrations
* Placeholder implementations
* Known instability

### Next Actions

* Recommended next implementation steps
* Remaining blockers
* Required approvals if applicable

---

## Completion Integrity Rules

Claude must never:

* mark scaffolded code as complete
* report assumed functionality without verification
* omit known implementation gaps
* collapse partially working systems into “done”
* claim production readiness without validation evidence

Repository status reporting must prioritize:

* accuracy
* auditability
* determinism
* reproducibility
* engineering honesty

---

## Repository Maturity Classification

Where applicable, entries should classify components as:

* Planned
* Scaffolded
* Partially Implemented
* Integrated
* Tested
* Verified
* Production Ready

This distinction is mandatory for AI-generated systems.

---

## Failure Recovery Rule

When failures occur, `PROGRESS.md` must document:

* root cause
* affected components
* corrective actions
* tests added
* prevention strategy
* remaining risks

Failures are considered repository learning events.

---

## Definition of Done Amendment

A task is not complete unless:

* implementation exists
* validation exists
* relevant tests pass
* documentation is updated
* and `PROGRESS.md` reflects the current repository state

## Definition of Done

A change is not complete unless:
- relevant unit tests exist and pass
- behavior-changing logic updates directives
- end-to-end impact is verified when applicable
- no secrets are introduced
- validation scripts pass
- changes are understandable by a junior developer

---

## Summary

Claude is the **planner, validator, and system hardener** — not the worker.

- Directives define intent
- Scripts execute deterministically
- Tests prove correctness
- Workers run the system
- Claude strengthens the system over time

**Be deliberate.  
Be testable.  
Be safe.  
Prefer systems over cleverness.**
