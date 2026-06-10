# CLAUDE.md
**[PROJECT_NAME] — Project Context for Claude Code**

<!-- STATIC: Edit this line manually. One sentence: what this project does and who it's for. -->
[Project description]

---
<!-- ================================================================
  SECTIONS BELOW MARKED [AUTO] ARE POPULATED/UPDATED BY /init
  SECTIONS MARKED [STATIC] ARE GOVERNANCE — DO NOT OVERWRITE
================================================================ -->

## Tech Stack
<!-- [AUTO] /init detects and fills this from lockfiles, manifests, config files -->

---

## Commands
<!-- [AUTO] /init detects common commands from package.json scripts, Makefile, pyproject.toml, README, etc. -->

```bash
# Install

# Run tests

# Start app / dev server

# Build / lint
```

---

## Layer Artifacts
<!-- [AUTO] /init scans and fills in which layer files exist.
     For greenfield projects with all 11 layers pre-generated, this section
     tells Claude exactly where to look instead of exploring from scratch. -->

| Layer | Artifact type | Location | Status |
|---|---|---|---|
| 1 Requirements | What to build | | |
| 2 Specs | Structure | | |
| 3 Directives | Behavior rules | `directives/` | |
| 4 Execution Plan | Build steps | | |
| 5 State Model | System states | | |
| 6 Test Scenarios | Validation | | |
| 7 System Loop | Runtime | | |
| 8 Failure Playbook | Failure handling | | |
| 9 Environment Model | Where it runs | | |
| 10 Data Lifecycle | Data over time | | |
| 11 Evolution Strategy | Change safely | | |

Leave a row blank if that layer is not yet formalized. Claude treats blank rows as absent, not as failures.

---

## Architecture
<!-- [AUTO] /init maps top-level folders and their responsibilities -->

---

## Key Files
<!-- [AUTO] /init identifies entry points, schema files, config files, and other high-value navigation anchors -->

---

<!-- ================================================================
  STATIC SECTION — DO NOT MODIFY WITH /init
================================================================ -->

## Essential Rules

1. Read the relevant `directives/` file before touching execution logic for that capability
2. Approval required before: schema changes, file deletes, production-impacting logic, large refactors
3. No secrets in repo — use `.env` (gitignored)
4. Explore → Plan → Build → Verify, in that order (see `AGENTS.md`)
5. All non-trivial logic needs a unit test; never mark scaffolded code as complete
6. Update `PROGRESS.md` after every meaningful change — capability maturity, not just "code added"

---

## Project Startup Checklist

On first session, Claude must:
- [ ] Read this file, `AGENTS.md`, and `directives/progress-tracking.md`
- [ ] Check whether `PROGRESS.md` exists — create it if not (one-time bootstrapping)
- [ ] Read the Layer Artifacts table above and locate the relevant artifacts for the current task
- [ ] Identify the highest-value maturity gap before writing any code

---

## Reference

- Operating contract and Claude's 4 roles → [`AGENTS.md`](AGENTS.md)
- PROGRESS.md governance → [`directives/progress-tracking.md`](directives/progress-tracking.md)
- Directives index → [`directives/README.md`](directives/README.md)
