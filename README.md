# FieldIQ Cricket Tactical Intelligence Platform

FieldIQ is a professional-grade cricket tactical intelligence and decision-support platform designed to analyze batter–bowler matchups, match state, delivery sequences, historical data, and fielder capabilities to generate and evaluate legal fielding configurations in an interactive 3D interface.

> [!IMPORTANT]
> **Governing Policy:** All development adheres strictly to [AGENTS.md](file:///C:/Users/ADMIN/Downloads/FieldIQ_V2/AGENTS.md). The system is decision-support software and must never claim to predict outcomes with certainty. Never invent unavailable data or bypass architectural layers.

---

## 1. Multi-Agent Collaboration Bridge

FieldIQ employs a multi-agent engineering workflow coordinating **ChatGPT / Codex**, **Cursor / Backend Agents**, **Antigravity**, and a **Human Approver**.

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

### Agent Roles

| Role | Agent | Responsibilities & Boundaries |
|---|---|---|
| **Coordinator** | `ChatGPT / Codex` | Work decomposition, task assignment, evidence review, priority management, human escalation. Does not edit files while claimed by an executor. |
| **Backend/ML Executor** | `backend_ml` (Cursor) | Python core, FastAPI, data pipelines, feature engineering, models, evaluations, rules, simulations, backend tests. |
| **Frontend Executor** | `antigravity` | React, TypeScript, Three.js, React Three Fiber, UI/UX, browser testing. **Must visualize backend output; must NOT invent tactical logic.** |
| **Human Approver** | `human` | Approves model promotions, secrets, architectural changes, destructive actions, and Git commits/pushes. |

### Source of Truth
- **Task Ledger:** [`Docs/FieldIQ/05_Operations/agent_task_ledger.json`](file:///C:/Users/ADMIN/Downloads/FieldIQ_V2/Docs/FieldIQ/05_Operations/agent_task_ledger.json)
- **Protocol:** [`Docs/FieldIQ/05_Operations/Agent Collaboration Protocol.md`](file:///C:/Users/ADMIN/Downloads/FieldIQ_V2/Docs/FieldIQ/05_Operations/Agent%20Collaboration%20Protocol.md)
- **File Ownership:** [`Docs/FieldIQ/05_Operations/file_ownership.json`](file:///C:/Users/ADMIN/Downloads/FieldIQ_V2/Docs/FieldIQ/05_Operations/file_ownership.json)
- **Handoff Reports:** `Docs/FieldIQ/05_Operations/handoffs/<task_id>_<date>.md`

---

## 2. Coordination CLI

The CLI tool [`scripts/ops/agent_task.py`](file:///C:/Users/ADMIN/Downloads/FieldIQ_V2/scripts/ops/agent_task.py) provides safe, process-isolated task ledger operations:

```powershell
# List all active tasks
python scripts/ops/agent_task.py list

# List ready tasks
python scripts/ops/agent_task.py list --status ready

# Claim a task
python scripts/ops/agent_task.py claim FIQ-0001 --agent backend_ml

# Submit a task for verification
python scripts/ops/agent_task.py verify FIQ-0001 --agent backend_ml

# Approve a task (Coordinator or Human)
python scripts/ops/agent_task.py approve FIQ-0001 --approver coordinator

# Complete a task
python scripts/ops/agent_task.py complete FIQ-0001 --agent coordinator

# View audit history
python scripts/ops/agent_task.py history FIQ-0001
```

---

## 3. Model Context Protocol (MCP) Server

FieldIQ provides an optional local MCP coordination server at [`scripts/ops/fieldiq_mcp_server.py`](file:///C:/Users/ADMIN/Downloads/FieldIQ_V2/scripts/ops/fieldiq_mcp_server.py).
- **Transport:** Standard I/O (`stdio`), newline-delimited JSON-RPC 2.0.
- **Tools Exposed:** `list_tasks`, `get_task`, `create_task`, `claim_task`, `update_task`, `submit_for_review`, `record_verification`, `request_human_approval`, `get_project_status`.
- **Safety Invariants:** No shell execution, no arbitrary file deletion, no secret retrieval, no automatic Git push, no automatic model promotion.
- **Disabling:** If MCP is unsupported in a client environment, remove it from `~/.gemini/config/mcp_config.json`; the shared JSON ledger and CLI remain the primary coordination mechanism.

See [`Docs/FieldIQ/05_Operations/MCP Coordination Server Specification.md`](file:///C:/Users/ADMIN/Downloads/FieldIQ_V2/Docs/FieldIQ/05_Operations/MCP%20Coordination%20Server%20Specification.md) for complete details.

---

## 4. Current Engineering Status

- **Backend / ML Engine:** Validated offline with zero data leakage across 3,646 matches and 819,957 deliveries from Cricsheet T20 International data.
- **Leakage-Safe Partitioning:** 70/15/15 match-disjoint split (2,552 train / 546 val / 548 holdout test matches). All career and within-match priors derived strictly from train or preceding balls.
- **Metric Reconciliation:** Resolved Brier Score and Log Loss formulas: $\text{Brier}_{\text{sum}} = 7.0 \times \text{Brier}_{\text{mean}}$. Reconciled XGBoost candidate (`1.4518` log loss, `0.7067` Brier sum / `0.1010` Brier mean) vs Multinomial Logistic Regression (`1.4282` log loss, `0.6930` Brier sum / `0.0990` Brier mean).
- **Model Promotion Governance:** Both candidate models remain honestly rejected in `models/model_registry.json` (`promoted: false`) due to wicket precision and boundary F1 thresholds under extreme class imbalance (~5.7% wickets). Production baseline `fieldiq_xgb_baseline_v1` remains the active model.
- **Live Frontend Integration:** Strictly deferred (`FIQ-0005`). React, TypeScript, Three.js, and React Three Fiber files are preserved completely intact for future interface integration.

---

## 5. Offline Verification Suites (230 Backend Tests)

Run backend verification tests offline without launching network servers or browser instances:

```powershell
# 1. Cricsheet Ingestion Pipeline Tests (12 tests)
.\.venv\Scripts\python.exe -m pytest tests/test_cricsheet_t20_pipeline.py -v

# 2. Causal Features & Model Evaluation Tests (11 tests)
.\.venv\Scripts\python.exe -m pytest tests/test_causal_features_and_model_evaluation.py -v

# 3. Candidate Field Intelligence Tests (18 tests)
.\.venv\Scripts\python.exe -m pytest tests/test_candidate_field_intelligence.py -v

# 4. Leakage & Metrics Reconciliation Tests (10 tests)
.\.venv\Scripts\python.exe -m pytest tests/test_leakage_and_metrics_reconciliation.py -v

# 5. Agent Coordination Bridge Tests (14 tests)
.\.venv\Scripts\python.exe -m pytest tests/test_agent_coordination.py -v

# 6. Complete Backend Test Suite (230 tests)
.\.venv\Scripts\python.exe -m pytest tests/ -q
```
