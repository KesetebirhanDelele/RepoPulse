# onboarding.md
**[PROJECT_NAME] — Junior Developer Onboarding Guide**

Read this before touching any code. It explains how this project is structured and what every file is for.

---

## Why this structure exists

Most projects fail not because developers can't write code, but because:
- No one agreed on what was being built before building it
- Failure cases were never designed, only discovered in production
- The system grew in ways no one planned or could safely change

This project uses an 11-layer blueprint to make all of those decisions visible before a single line of code is written.

---

## The 4 Zones

The 11 layers are grouped into 4 zones. Each zone covers a different stage of building and running a system.

```
DESIGN  → What are we building and how should it behave?
BUILD   → How do we build it, test it, and track its states?
OPERATE → How does it run, fail, and recover in the real world?
ADAPT   → How does it change safely over time?
```

---

## The 11 Layers

### DESIGN ZONE

**Layer 1 — Requirements** (`spec/01-requirements.md`)
What the system must do.
Read this first. If you are unsure what a feature should do, this is the answer. If the answer is not here, the requirements need updating before you write code.

**Layer 2 — Specifications** (`spec/02-specs.md`)
The structure of the system — data models, API shapes, component architecture.
Read this before designing anything new. If your change affects a data shape or API contract, update this file first.

**Layer 3 — Directives** (`directives/`)
The rules the system must follow when operating.
One file per capability. Read the relevant directive before modifying any logic in that area. If a business rule changes, update the directive before changing the code.

---

### BUILD ZONE

**Layer 4 — Execution Plan** (`execution/04-execution-plan.md`)
The order in which things get built, with milestones and dependencies.
Check this when starting a new feature. It tells you what needs to exist before your work can begin.

**Layer 5 — State Model** (`state/05-state-model.md`)
Every state the system can be in and how it moves between states.
Check this before adding or changing any status field, workflow step, or lifecycle event. Invalid state transitions are a common source of hard-to-find bugs.

**Layer 6 — Test Scenarios** (`tests/06-test-scenarios.md`)
The scenarios that prove the system works — happy paths, edge cases, and failures.
Tests are designed here first, then implemented in code. If you are writing a test, check whether the scenario is already defined here.

---

### OPERATE ZONE

**Layer 7 — System Loop** (`runtime/07-system-loop.md`)
How the system runs in production — background jobs, scheduled tasks, event triggers.
Read this before changing anything that runs automatically or on a schedule.

**Layer 8 — Failure Playbook** (`failure/08-failure-playbook.md`)
What the system does when things go wrong.
Every external call can fail. Every job can time out. This file defines what happens in each case. Read it before adding a new integration or changing error handling.

**Layer 9 — Environment & Configuration** (`environment/09-environment.md`)
How the system is configured in dev, staging, and production.
Never hardcode environment-specific values. Check this file for the right variable names and understand which environments are safe to modify.

---

### ADAPT ZONE

**Layer 10 — Data Lifecycle** (`data/10-data-lifecycle.md`)
How data is created, changed, retained, and deleted over time.
Before adding a new table, field, or deletion routine, check what rules apply to that data.

**Layer 11 — Evolution Strategy** (`evolution/11-evolution-strategy.md`)
How the system changes safely — schema migrations, API versioning, rollout strategy.
Before making a breaking change to a schema or API, read this. Breaking changes need a migration plan.

---

## UX and User Interface

UX is not a separate layer. It is considered within each zone:

- In **DESIGN**: user flows and personas are part of requirements and specs
- In **BUILD**: UI states are part of the state model; interaction flows are part of test scenarios
- In **OPERATE**: error messages and loading states are part of the system loop and failure playbook
- In **ADAPT**: design system changes are part of the evolution strategy

For UI-heavy projects, look for `ux/12-interaction-model.md` which consolidates all UX decisions in one place.

---

## How to work on this project

**Starting a new feature:**
1. Read `spec/01-requirements.md` — is this feature defined?
2. Read the relevant `directives/` file — what rules apply?
3. Check `state/05-state-model.md` — does this feature change any state?
4. Write your test scenarios first (`tests/06-test-scenarios.md`)
5. Implement the code
6. Update `PROGRESS.md`

**Fixing a bug:**
1. Read the relevant `directives/` file — is the correct behavior defined?
2. Check `failure/08-failure-playbook.md` — is this failure case covered?
3. Add a test scenario for the bug before fixing it
4. Fix the code, update the directive if the rule was wrong

**Changing a data model:**
1. Read `spec/02-specs.md` — understand the current structure
2. Read `data/10-data-lifecycle.md` — what rules apply to this data?
3. Read `evolution/11-evolution-strategy.md` — how do schema changes get rolled out?
4. Write a migration plan before touching the schema

---

## What is PROGRESS.md?

`PROGRESS.md` tracks how mature each capability is across the 11 layers.

It is not a task list. It is a maturity scorecard. It answers: "For this capability, how complete is the design? The tests? The failure handling? The environment model?"

Check it at the start of every work session to understand what is done and what is next. Update it when you complete or discover work. Never mark something as done just because the code exists.

---

## What is CLAUDE.md?

`CLAUDE.md` is a short file that tells Claude Code (the AI assistant) exactly where each layer file lives. It also lists the key commands, architecture map, and essential rules for this project.

When Claude Code starts a session, it reads `CLAUDE.md` first. This prevents it from scanning the whole repo to orient itself, saving time and cost.

You do not need to edit `CLAUDE.md` manually. It is updated by running `/init` in Claude Code.

---

## What is AGENTS.md?

`AGENTS.md` defines how Claude Code behaves in this project — its 4 operational roles (Explore, Plan, Build, Verify), testing rules, approval gates, and the mapping from the 11 layers to folder locations.

You do not need to read this regularly. It is reference material for understanding why Claude Code behaves the way it does.
