# directives/
**Behavior rules, SOPs, and runbooks**

Directives are Layer 3 of the 11-layer capability framework — they define *how the system should behave*, distinct from code (which implements it) and tests (which prove it).

Claude must read the relevant directive before modifying execution logic for that capability.
This file is a template. `/init` scans the project and fills in the Discovered Layers table below.

---

## What a directive is

A directive is a plain-language document that defines:
- what a capability does
- what inputs and outputs are expected
- what edge cases and constraints apply
- what safety rules govern it
- how to verify it worked

It is not code. It is not a prompt. It is the authoritative statement of intent for a capability.

---

## Current Directives

| File | Capability | 11-Layer coverage |
|---|---|---|
| [progress-tracking.md](progress-tracking.md) | PROGRESS.md governance — session startup, update rules, maturity assessment | Layers 1–6, 8 |
<!-- Add rows here as new directives are created -->

---

## Discovered Layer Artifacts
<!-- [AUTO] /init scans the project and fills in this table.
     Each row represents a layer artifact found in the repo.
     Blank rows mean the layer is not yet formalized. -->

| Layer | Artifact | Location | Formalized? |
|---|---|---|---|
| 1 Requirements | | | |
| 2 Specs | | | |
| 3 Directives | This folder | `directives/` | Yes |
| 4 Execution Plan | | | |
| 5 State Model | | | |
| 6 Test Scenarios | | | |
| 7 System Loop | | | |
| 8 Failure Playbook | | | |
| 9 Environment Model | | | |
| 10 Data Lifecycle | | | |
| 11 Evolution Strategy | | | |

---

## How to add a directive

1. Create `directives/<capability-name>.md`
2. Include: purpose, inputs, outputs, edge cases, safety constraints, verification steps
3. Add a row to the Current Directives table above
4. Reference the directive from the relevant execution file (one-line comment at the top)
5. Update `PROGRESS.md` — adding a directive advances Layer 3 maturity for that capability
