# System Architecture

FieldIQ is decision-support software. It must not claim to predict cricket
outcomes with certainty.

## Tool roles

| Tool | Responsibility |
| --- | --- |
| Obsidian (`Docs/FieldIQ`) | Requirements, contracts, task assignments, status |
| Cursor | Python, FastAPI, validation, data, ML, tests |
| Antigravity | React, Three.js, UI, 3D field, browser testing |
| Git | Branches, diffs, review, merging |

Obsidian does not drive the agents by itself. Each coordinated task has one
note that both Cursor and Antigravity read.

Agents work from the repository root
(`C:\Projects\cricket-tactical-intelligence`) because `AGENTS.md`, `backend/`,
`frontend/`, and `tests/` sit outside this vault.

## Layers

Keep these layers separate. Do not bypass a layer without documenting why.

DATA
→ FEATURE ENGINEERING
→ PLAYER INTELLIGENCE
→ MATCHUP INTELLIGENCE
→ MATCH STATE
→ SEQUENCE INTELLIGENCE
→ OUTCOME PREDICTION
→ FIELD GENERATION
→ OPTIMIZATION
→ SIMULATION
→ RULE VALIDATION
→ EXPLANATION
→ HUMAN DECISION
→ 3D VISUALIZATION

Current functional work is at the data ingestion boundary: canonical CSV
validation and explicit source-column mapping. Later layers are not connected
and must not be simulated as complete.

## Contracts

- [[CSV Dataset Contract]]
- [[Backend API Contract]]

## Operating rule

Obsidian defines what must be built. Contracts define how components
communicate. Cursor and Antigravity implement separate ownership areas. Git
preserves reviewable history. No commit or push happens before human approval.
