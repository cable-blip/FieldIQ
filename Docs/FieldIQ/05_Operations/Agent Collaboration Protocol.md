# FieldIQ Agent Collaboration Protocol

## 1. Overview & Purpose

This document establishes the binding multi-agent collaboration protocol for **FieldIQ**, a professional-grade cricket tactical intelligence and decision-support platform (`C:\Users\ADMIN\Downloads\FieldIQ_V2`).

FieldIQ development involves heterogeneous engineering agents:
- **ChatGPT / Codex**: Task planner, reviewer, decomposition coordinator.
- **Cursor / Backend ML Executor**: Python, FastAPI, ML pipelines, data ingestion, feature engineering, simulations, model governance.
- **Antigravity**: React, TypeScript, Three.js, React Three Fiber, UI/UX, browser testing.
- **Human Approver**: Architecture governance, model promotion, secrets, sensitive approvals.

To prevent conflicting edits, unauthorized model promotions, phantom completions, and cross-agent race conditions, all agent activity must strictly follow this protocol and synchronize through the **Shared FieldIQ Task Ledger** (`Docs/FieldIQ/05_Operations/agent_task_ledger.json`).

Treat `AGENTS.md` as the overarching project policy.

---

## 2. Collaboration Workflow

The governing collaboration workflow is structured as a strict handoff pipeline:

```text
ChatGPT / Codex
      ↓
Task planner and reviewer (FIQ-XXXX decomposed into ledger)
      ↓
Shared FieldIQ Task Ledger (agent_task_ledger.json)
      ↓
Executor claims task (Backend/ML or Antigravity)
      ↓
Implementation within strict file scope
      ↓
Tests & Offline Verification (Verification commands run)
      ↓
Task updated in ledger & Handoff Report generated
      ↓
ChatGPT / Codex reviews evidence & artifacts
      ↓
Human Approval for sensitive actions (secrets, promotion, git push)
```

### Governing Invariants:
1. **No Unclaimed Work**: Agents must never create or execute code changes outside an approved, claimed task in the ledger.
2. **No Blind Concurrent Overwrites**: ChatGPT/Codex must not modify files while Antigravity or Cursor is editing them.
3. **No Unilateral Scope Expansion**: Files outside `scope.allowed_files` are strictly forbidden from modification. If cross-cutting files are required, the task must be flagged `coordination_required`.
4. **No Fake Completion**: A task is never marked `completed` without reproducible verification commands, exact exit codes, and an audit trail in `Docs/FieldIQ/05_Operations/handoffs/`.
5. **No Automatic Commits or Pushes**: Neither agents nor coordination scripts may execute automatic Git commits or Git pushes.

---

## 3. Agent Roles & Responsibilities

### 3.1 Coordinator (`coordinator` — ChatGPT / Codex)
- **Primary Responsibilities**:
  - Decomposes high-level requirements into atomic, verifiable tasks.
  - Formulates unambiguous acceptance criteria and verification commands.
  - Assigns initial ownership, dependencies, and priorities.
  - Reviews execution evidence, test logs, and handoff reports.
  - Detects contradictions, scope creep, or architectural regressions.
  - Maintains `PROJECT_STATUS.md` and documentation sync.
  - Escalates to the Human Approver only when strictly necessary.
- **Limitations**:
  - Does not directly execute code or bypass the task ledger.
  - Does not touch executor-owned source code while an executor holds an active claim.

### 3.2 Backend / ML Executor (`backend_ml` — Cursor / Backend Agent)
- **Primary Responsibilities**:
  - Python source code (`backend/app/`), scripts (`scripts/`), data pipelines, and test suites (`tests/`).
  - FastAPI routers, services, schemas, and API contracts.
  - Causal feature engineering, dataset validation, data leakage prevention.
  - Model training, benchmarking, probability calibration, and metric evaluation.
  - Simulation engines, spatial intelligence, and ICC rules engines.
  - Backend unit, integration, and golden acceptance test execution.
- **Limitations**:
  - Does not promote models to active production without human approval.
  - Does not invent cricket tactical logic outside data-driven models and verified rules.

### 3.3 Frontend Executor (`antigravity` — Antigravity Agent)
- **Primary Responsibilities**:
  - React, TypeScript, Three.js, React Three Fiber, CSS/Tailwind UI/UX (`frontend/`).
  - 3D stadium, pitch, stumps, wagon wheel, boundary, and interactive fielder placement rendering.
  - Client contracts, UI state management, and what-if simulation UI controls.
  - Browser and component testing (Vitest, Playwright, Chrome DevTools).
- **Governing Constraints (`AGENTS.md` Rule 10)**:
  - The frontend executor visualizes tactical intelligence produced by the backend.
  - It must **NOT** independently invent cricket tactical logic, heuristic multipliers, or client-side legality logic.
  - Live frontend interface changes must be explicitly authorized via ledger tasks; otherwise, frontend contracts must be preserved without unauthorized modification.

### 3.4 Human Approver (`human`)
- **Primary Responsibilities**:
  - Holds final authority on system architecture and product decisions.
  - Approves model promotion from candidate to active production.
  - Provides credentials, API keys, and environment secrets when required.
  - Approves destructive actions (file deletion, cache purge, schema migration).
  - Approves Git commits and pushes to remote repositories.
  - Resolves conflicting requirements or trade-offs that cannot be decided algorithmically.

---

## 4. Task Lifecycle & State Machine

Every task in the ledger progresses through an explicit state machine:

```text
[ backlog ]
     ↓
  [ ready ]  ← (dependencies satisfied & acceptance criteria defined)
     ↓
 [ claimed ]  ← (assigned agent claims task; sets claimed_at)
     ↓
[ in_progress ]  ← (agent working within allowed_files)
     ↓
[ verification ]  ← (code frozen; running verification commands)
     ↓
[ review_required ]  ← (handoff report written; awaiting coordinator / human review)
     ↓
 [ approved ]  ← (coordinator validates evidence; human approves if sensitive)
     ↓
[ completed ]  ← (changes integrated, verified, and logged)
```

Alternative exit and pause paths:
- `in_progress` → `blocked`: Agent encounters an external blocker, missing dependency, or conflict.
- `review_required` → `rejected`: Reviewer identifies failed criteria, unverified claims, or leaked data.
- `*` → `cancelled`: Task is superseded, obsolete, or revoked by coordinator/human.

### State Transition Rules:
| Current State | Permitted Next States | Authorized Agent | Conditions |
|---|---|---|---|
| `backlog` | `ready`, `cancelled` | `coordinator`, `human` | Acceptance criteria and scope defined. |
| `ready` | `claimed`, `backlog`, `cancelled` | `backend_ml`, `antigravity`, `coordinator` | Dependencies satisfied. |
| `claimed` | `in_progress`, `ready` (release) | Claim owner | Task claimed atomically by owner. |
| `in_progress` | `verification`, `blocked`, `ready` (release) | Claim owner | Scope verified; tests prepared. |
| `blocked` | `in_progress`, `ready`, `cancelled` | Any agent / human | Blocker resolved and documented. |
| `verification` | `review_required`, `in_progress` | Claim owner | All verification commands executed. |
| `review_required` | `approved`, `rejected`, `in_progress` | `coordinator`, `human` | Handoff report inspected. |
| `approved` | `completed` | `coordinator`, `human` | Final validation passed. |
| `rejected` | `in_progress`, `ready`, `cancelled` | `coordinator`, `human` | Rejection feedback logged in notes. |

---

## 5. File Ownership & Boundary Protection

To prevent concurrent conflicting edits, file paths are partitioned by default ownership:

| Partition | Default Owner | Description |
|---|---|---|
| `backend/**`, `scripts/**`, `tests/**`, `models/**`, `data/**`, `rules/**`, `simulation/**` | `backend_ml` | Python core, ML pipelines, tests, and domain engines |
| `frontend/**` | `antigravity` | React, Three.js, Vitest, UI components, assets |
| `PROJECT_STATUS.md`, `Docs/**` | `coordinator` | Architecture specifications, status ledger, documentation |
| `.env`, `.env.*`, `security/**`, production secrets | `human_only` | Credentials, secrets, sensitive operational configurations |

### Coordination Required Rule:
If a task touches files spanning multiple ownership partitions (e.g. updating a FastAPI router schema and the corresponding frontend TypeScript API contract):
1. The task must declare `approval_required: true` and specify the cross-boundary scope in `scope.allowed_files`.
2. The executor must coordinate with the owning agent or request human sign-off before modifying files outside its default partition.
3. Neither agent may modify files designated as `human_only`.

---

## 6. Handoff Procedure & Audit Artifacts

Whenever an executor transitions a task to `review_required` or `completed`, it **MUST** generate an immutable handoff report:

`Docs/FieldIQ/05_Operations/handoffs/<task_id>_<YYYYMMDD>.md`

The handoff report must contain:
1. **Task ID & Title**: Exact match with ledger.
2. **Executing Agent**: Identity of the executor.
3. **Objective**: Concrete problem solved.
4. **Assumptions & Domain Constraints**: Explicit assumptions.
5. **Files Changed**: Exact list of files created or modified.
6. **Files Not Changed (Guarded)**: Key sensitive files intentionally untouched.
7. **Verification Commands**: Exact commands executed in the environment.
8. **Exit Codes & Outputs**: Verifiable test output and exit code (must be 0 for passing tests).
9. **Known Limitations & Edge Cases**: What was NOT addressed or where data is sparse.
10. **Unresolved Questions**: Open technical or tactical questions.
11. **Requested Next Action**: Next recommended step for coordinator.
12. **Approval Status**: Whether human approval is required and granted.

---

## 7. Human Interruption Rules

Agents must respect human attention. **Agents must only interrupt the human user when one of the following occurs:**
1. A secret, API key, database password, or private credential is required.
2. A destructive action is proposed (e.g. deleting files, dropping tables, wiping cached raw data).
3. A database or data schema migration is required.
4. A machine learning model is candidate for production promotion.
5. A Git commit or Git push to remote repository is requested.
6. Two requirements or domain specifications directly conflict.
7. An architectural change is proposed (e.g. replacing FastAPI, introducing a new database, changing core optimizer pipeline).
8. A private, proprietary, or licensed dataset requires usage authorization.
9. A test cannot be made reliable without modifying its acceptance criteria.
10. The executor is blocked after all safe, documented alternatives are exhausted.

**Agents must NOT interrupt the human for:**
- Normal read-only file inspection and code exploration.
- Routine offline unit/integration test runs.
- Code formatting, linting, and type checking.
- Routine documentation updates and task status bookkeeping.
- Non-destructive bug diagnosis and isolated debugging.
- Generating handoff markdown reports.
- Routine dependency inspection.

---

## 8. Model Governance & Promotion Invariants

Per `AGENTS.md` Rule 15 and `Docs/FieldIQ/01_Architecture/ML Model Governance.md`:
1. **Never Silently Replace Production Models**: The active production model pointer (`models/model_registry.json`) can only be modified with explicit human sign-off.
2. **Promotion Checklist Enforcement**: Every candidate model must satisfy all documented promotion gates:
   - Wicket Recall $\ge 0.150$ and Wicket Precision $\ge 0.100$.
   - Boundary $F_1 \ge 0.350$ and Boundary PR-AUC $>$ empirical baseline.
   - Holdout Test Log Loss $\le 1.350$ and Brier Score $\le 0.700$.
   - Valid continuous probability distribution ($\sum_{i=0}^6 P_i = 1.0 \pm 10^{-4}$).
   - 3-Split match-disjoint data stability (log-loss range $\le 0.05$).
3. **Rejected Candidates Retained**: If any gate fails, the model must remain recorded as `promoted: false`. It must never be silently activated.
4. **Honest Baseline Disclosure**: When uncalibrated baseline models are served, the system must explicitly expose `status: "uncalibrated_baseline"` with measured recall/precision.

---

## 9. Security & Sandbox Invariants

1. **Local Security**:
   - Never commit `.env` or secrets. Use `.env.example` as template.
   - Never print or log API keys, tokens, or private credentials in task ledgers, handoff reports, or CLI outputs.
2. **Execution Safety**:
   - Coordination utilities and MCP servers must never execute arbitrary shell commands automatically.
   - Coordination tools must never run `git push`, `rm -rf`, or file deletion commands without interactive human approval.
   - Coordination files are written atomically using temporary files and safe renames to prevent corruption during concurrent reads.
