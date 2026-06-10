# AGENTS.md
**Universal Operating Contract for Claude and AI Coding Agents**

Copy this file as-is to any project. It does not contain project-specific content.
It is not modified by `/init`. Update it only when your team's operating rules change.

---

## Core Principle

LLMs are probabilistic. Production systems must be deterministic.

Claude's role is to reason, plan, orchestrate, and validate — never to be the runtime executor of business logic, tests, or workflows.

---

## Claude's 4 Operational Roles

These describe how Claude Code operates in sequence. They are distinct from the 11-layer capability framework used to assess maturity.

### 1. Explore
Before touching any code, Claude must:
- Read the relevant directive in `directives/`
- Read the Layer Artifacts table in `CLAUDE.md` and navigate directly to relevant files
- Understand the current capability maturity from `PROGRESS.md`
- Identify what already exists before proposing any change

Never skip Explore. Reading wrong files is cheaper than writing wrong code.

### 2. Plan
Before writing any code, Claude must:
- Define the minimum change needed to close the target maturity gap
- Design the test scenario first
- Identify approval gates (schema changes, deletes, production impact)
- Ask for clarification when intent is ambiguous

### 3. Build
When writing code, Claude must:
- Stay in the correct layer — no business logic in directives, no orchestration in execution scripts
- Make the minimum necessary change — no speculative features or abstractions
- Write for clarity, reproducibility, and teachability
- One script or function = one clear responsibility

### 4. Verify
After writing code, Claude must:
- Run the test suite and read the output
- Confirm behavior matches the relevant directive
- Update `PROGRESS.md` with honest capability maturity
- Flag any unverified areas explicitly

---

## Folder Responsibilities

| Folder | Purpose | Does NOT contain |
|---|---|---|
| `directives/` | Behavior rules, SOPs, runbooks (Layer 3) | Code, prompts, orchestration logic |
| `spec/` | Requirements and structural specs (Layers 1–2) | Implementation detail |
| `execution/` or equivalent | Deterministic scripts and logic | Orchestration, prompts |
| `tests/` | Automated verification | Business logic |
| `configs/` | Environment identifiers | Secrets |
| `scripts/` | Runtime runners | Business logic |
| `tmp/` | Scratch — always safe to delete | Anything committed |

---

## Testing Rules

### Unit Tests
- All non-trivial execution logic must have unit tests
- Pure logic only — no I/O, no DB, no network
- External dependencies mocked
- Fast, deterministic, runnable locally without credentials

### Integration Tests
- May touch dev sandboxes, test DBs, or mock APIs
- Must never touch production
- Require explicit opt-in via env flag or CI label

### End-to-End / UI Tests
- Validate routes, forms, auth flows, permissions, and UI state
- Browser automation (e.g. Playwright) preferred
- Claude defines test matrices and scenarios; tools execute them
- Claude must not simulate UI behavior in prose

### Worker / Script Tests
- Test routing logic: correct script selection, retry behavior, idempotency
- Workers must never send real communications during tests

### Directive Validation
- Directives must have: required sections present, referenced files existing, clarity for a junior developer

---

## Claude Operating Rules

### 1. Never act blindly
Read the relevant directive before touching execution code. If no directive exists for the capability, ask before creating one.

### 2. Never mix layers
- No business logic in directives
- No orchestration logic in execution scripts
- No test simulation inside Claude responses

### 3. Prefer deterministic verification
If behavior can be tested via code, do not validate it narratively.

### 4. Approval-gated changes
Request approval before:
- Large refactors
- Schema changes
- Deleting files
- Production-impacting logic
- Modifying safety, compliance, or testing baselines

### 5. Self-Annealing Loop
When something fails:
1. Identify the root cause
2. Fix the script or logic
3. Add or update the test
4. Update the relevant directive
5. Confirm the system is stronger

Failures are repository learning events, not mistakes.

---

## 11-Layer Framework → Repo Location Pattern

Capability maturity is assessed across 11 layers. The Layer Artifacts table in `CLAUDE.md` maps these to actual file paths for the current project. This table shows the default pattern.

| Zone | Layer | Artifact type | Default location pattern |
|---|---|---|---|
| **DESIGN** | 1 Requirements | What to build | `spec/requirements.md` |
| | 2 Specs | Structure | `spec/specs.md` |
| | 3 Directives | Behavior rules | `directives/<capability>.md` |
| **BUILD** | 4 Execution Plan | Build steps | `directives/execution-plan.md` |
| | 5 State Model | System states | `directives/state-model.md` |
| | 6 Test Scenarios | Validation | `tests/` + `directives/test-scenarios.md` |
| **OPERATE** | 7 System Loop | Runtime | `scripts/` or `services/worker/` |
| | 8 Failure Playbook | Failure handling | `directives/failure-playbook.md` |
| | 9 Environment Model | Where it runs | `configs/` + `.env` |
| **ADAPT** | 10 Data Lifecycle | Data over time | `directives/data-lifecycle.md` |
| | 11 Evolution Strategy | Change safely | `directives/evolution-strategy.md` |
| *(+UI)* | UX / Interface | User interaction | Assessed within each zone — not a standalone layer |

Not all layers require a formal artifact. Classify absent layers as: not applicable, not yet needed, implicit, or not yet formalized. Do not force structure onto a project to satisfy the layer model.

---

## Tooling Assumptions

Claude may assume:
- Claude Code CLI is available
- A code editor (VS Code, Cursor, etc.) may be in use
- Git is present
- CI may run automated tests

Claude must not assume:
- Production credentials exist locally
- Proprietary automation platforms exist

---

## Intern Safety Rules

Any project may be worked on by junior developers or interns.

- No destructive scripts without confirmation
- No production writes without explicit environment checks
- No secrets in repo
- Setup must complete in one command
- Tests must run in one command

Optimize for: clarity, reproducibility, teachability.
