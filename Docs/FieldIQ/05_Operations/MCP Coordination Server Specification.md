# FieldIQ MCP Coordination Server Specification

## 1. Overview & Purpose

The **FieldIQ MCP Coordination Server** (`scripts/ops/fieldiq_mcp_server.py`) implements the open Model Context Protocol (MCP) standard to provide a safe, structured coordination layer between LLM agents (ChatGPT/Codex, Antigravity, Cursor) and the FieldIQ task ledger.

It exposes bounded, auditable operations for task lifecycle management, status reporting, and evidence recording while strictly eliminating execution risks.

---

## 2. Server Transport & Launch

- **Transport**: Standard Input/Output (`stdio`) with newline-delimited JSON-RPC 2.0.
- **Protocol Version**: `2024-11-05`
- **SDK Dependencies**: Zero external dependencies (uses standard Python library `sys`, `json`, `os`, `pathlib`).
- **Local Launch Command**:
  ```powershell
  python scripts\ops\fieldiq_mcp_server.py
  ```

### Configuration in Antigravity / Agent Environments

To configure globally in Antigravity (`~/.gemini/config/mcp_config.json`):
```json
{
  "mcpServers": {
    "fieldiq-coordinator": {
      "command": "python",
      "args": [
        "C:\\Users\\ADMIN\\Downloads\\FieldIQ_V2\\scripts\\ops\\fieldiq_mcp_server.py"
      ],
      "env": {
        "PYTHONUNBUFFERED": "1"
      }
    }
  }
}
```

### How to Disable It
- To disable the MCP server, remove or comment out the `"fieldiq-coordinator"` entry from `~/.gemini/config/mcp_config.json`.
- The system will seamlessly fall back to the task ledger (`agent_task_ledger.json`), the CLI wrapper (`scripts/ops/agent_task.py`), and handoff markdown files (`Docs/FieldIQ/05_Operations/handoffs/`).

---

## 3. Exposed Coordination Tools

The MCP server exposes strictly the following 9 coordination tools:

| Tool Name | Purpose | Mutation |
|---|---|---|
| `list_tasks` | List tasks in ledger with optional `status` and `owner` filters. | Read-Only |
| `get_task` | Retrieve full task record, scope, criteria, test logs, and history. | Read-Only |
| `create_task` | Create a new task with defined scope, criteria, and dependencies. | Ledger Write |
| `claim_task` | Claim a ready task for execution by an authorized agent. | Ledger Write |
| `update_task` | Record task notes or verified changed files within declared scope. | Ledger Write |
| `submit_for_review` | Transition verified task to review; auto-generates handoff report. | Ledger Write |
| `record_verification` | Record an executed test command, its exit code, and summary. | Ledger Write |
| `request_human_approval`| Flag task as requiring human intervention. | Ledger Write |
| `get_project_status` | Retrieve verified high-level project summary and governance state. | Read-Only |

---

## 4. Input & Output Schemas

### 4.1 `list_tasks`
- **Input Schema**:
  ```json
  {
    "type": "object",
    "properties": {
      "status": {"type": "string", "description": "Filter by task status"},
      "owner": {"type": "string", "description": "Filter by task owner"}
    }
  }
  ```
- **Output Schema**: Array of task summary objects (`task_id`, `title`, `owner`, `status`, `priority`, `approval_required`).

### 4.2 `get_task`
- **Input Schema**:
  ```json
  {
    "type": "object",
    "properties": {
      "task_id": {"type": "string", "description": "Task identifier formatted FIQ-XXXX"}
    },
    "required": ["task_id"]
  }
  ```
- **Output Schema**: Complete task JSON record.

### 4.3 `create_task`
- **Input Schema**:
  ```json
  {
    "type": "object",
    "properties": {
      "task_id": {"type": "string"},
      "title": {"type": "string"},
      "description": {"type": "string"},
      "owner": {"type": "string", "enum": ["coordinator", "backend_ml", "antigravity", "human"]},
      "priority": {"type": "string", "enum": ["critical", "high", "medium", "low"]},
      "allowed_files": {"type": "array", "items": {"type": "string"}},
      "forbidden_files": {"type": "array", "items": {"type": "string"}},
      "dependencies": {"type": "array", "items": {"type": "string"}},
      "acceptance_criteria": {"type": "array", "items": {"type": "string"}},
      "verification_commands": {"type": "array", "items": {"type": "string"}},
      "approval_required": {"type": "boolean"},
      "status": {"type": "string"}
    },
    "required": ["task_id", "title", "description", "owner"]
  }
  ```
- **Output Schema**: `{"status": "created", "task": {...}}`

### 4.4 `claim_task`
- **Input Schema**:
  ```json
  {
    "type": "object",
    "properties": {
      "task_id": {"type": "string"},
      "agent": {"type": "string", "enum": ["coordinator", "backend_ml", "antigravity", "human"]}
    },
    "required": ["task_id", "agent"]
  }
  ```
- **Output Schema**: `{"status": "claimed", "task": {...}}`

### 4.5 `update_task`
- **Input Schema**:
  ```json
  {
    "type": "object",
    "properties": {
      "task_id": {"type": "string"},
      "agent": {"type": "string"},
      "notes": {"type": "string"},
      "files_changed": {"type": "array", "items": {"type": "string"}}
    },
    "required": ["task_id", "agent"]
  }
  ```
- **Output Schema**: `{"status": "updated", "task": {...}}`

### 4.6 `submit_for_review`
- **Input Schema**:
  ```json
  {
    "type": "object",
    "properties": {
      "task_id": {"type": "string"},
      "agent": {"type": "string"},
      "summary": {"type": "string"}
    },
    "required": ["task_id", "agent"]
  }
  ```
- **Output Schema**: `{"status": "review_required", "task": {...}}`

### 4.7 `record_verification`
- **Input Schema**:
  ```json
  {
    "type": "object",
    "properties": {
      "task_id": {"type": "string"},
      "agent": {"type": "string"},
      "command": {"type": "string"},
      "exit_code": {"type": "integer"},
      "output_summary": {"type": "string"}
    },
    "required": ["task_id", "agent", "command", "exit_code"]
  }
  ```
- **Output Schema**: `{"status": "recorded", "task": {...}}`

### 4.8 `request_human_approval`
- **Input Schema**:
  ```json
  {
    "type": "object",
    "properties": {
      "task_id": {"type": "string"},
      "requester": {"type": "string"},
      "reason": {"type": "string"}
    },
    "required": ["task_id", "requester", "reason"]
  }
  ```
- **Output Schema**: `{"status": "approval_requested", "task": {...}}`

### 4.9 `get_project_status`
- **Input Schema**: `{}` (Empty object)
- **Output Schema**: High-level status object (`project`, `coordination_ledger`, `total_tasks`, `task_breakdown`, `governing_policy`, `model_governance`, `frontend_status`).

---

## 5. Approval Behavior & Security Invariants

The MCP server enforces strict security boundaries:
1. **No Arbitrary Command Execution**: The MCP server never runs shell commands on behalf of an agent. It records test commands and results that agents execute in their own secure terminal sandboxes.
2. **No Arbitrary File Deletion or Overwrite**: The MCP server cannot delete files or write to arbitrary locations; it only manipulates the ledger JSON and handoff markdown files via atomic writes.
3. **No Secret Retrieval or `.env` Exposure**: Any attempt to submit text containing secrets, API keys, tokens, or private keys is automatically scrubbed using regex redaction. `.env` files are rejected from task scope.
4. **No Automatic Git Push / Commit**: Neither the MCP server nor coordination scripts perform Git commits or pushes.
5. **No Automatic Model Promotion**: Candidate models marked `promoted: false` cannot be promoted or activated through the MCP server without explicit human authorization.
