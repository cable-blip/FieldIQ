#!/usr/bin/env python3
"""
scripts/ops/fieldiq_mcp_server.py
---------------------------------
Local Model Context Protocol (MCP) server for FieldIQ Multi-Agent Coordination.

Implements standard MCP JSON-RPC 2.0 over stdio transport.
Exposes strictly bounded, safe coordination tools:
  - list_tasks
  - get_task
  - create_task
  - claim_task
  - update_task
  - submit_for_review
  - record_verification
  - request_human_approval
  - get_project_status

Security Invariants:
  - Zero arbitrary shell execution.
  - Zero arbitrary file deletion.
  - Zero secret or .env exposure.
  - Zero automatic Git push or commits.
  - Zero unauthorized model promotion.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.services.agent_coordination import (
    AgentTaskLedger,
    CoordinationError,
    redact_secrets,
)

SERVER_NAME = "fieldiq-coordination-mcp"
SERVER_VERSION = "1.0.0"
PROTOCOL_VERSION = "2024-11-05"

# Tool schemas
TOOLS = [
    {
        "name": "list_tasks",
        "description": "List tasks from the FieldIQ task ledger with optional filtering by status and owner.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "description": "Filter by task status (backlog, ready, claimed, in_progress, blocked, verification, review_required, approved, completed, rejected, cancelled)",
                },
                "owner": {
                    "type": "string",
                    "description": "Filter by task owner (coordinator, backend_ml, antigravity, human)",
                },
            },
        },
    },
    {
        "name": "get_task",
        "description": "Retrieve the full task record, scope, criteria, test results, and audit history by task ID.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "Task identifier formatted as FIQ-XXXX (e.g. FIQ-0001)",
                },
            },
            "required": ["task_id"],
        },
    },
    {
        "name": "create_task",
        "description": "Create a new task in the FieldIQ task ledger with defined scope and acceptance criteria.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "Unique task ID (e.g. FIQ-0007)"},
                "title": {"type": "string", "description": "Short task title"},
                "description": {"type": "string", "description": "Precise task description"},
                "owner": {"type": "string", "enum": ["coordinator", "backend_ml", "antigravity", "human"]},
                "priority": {"type": "string", "enum": ["critical", "high", "medium", "low"], "default": "medium"},
                "allowed_files": {"type": "array", "items": {"type": "string"}, "description": "Allowed files/globs"},
                "forbidden_files": {"type": "array", "items": {"type": "string"}, "description": "Forbidden files/globs"},
                "dependencies": {"type": "array", "items": {"type": "string"}, "description": "Prerequisite task IDs"},
                "acceptance_criteria": {"type": "array", "items": {"type": "string"}, "description": "Acceptance criteria list"},
                "verification_commands": {"type": "array", "items": {"type": "string"}, "description": "Commands to verify"},
                "approval_required": {"type": "boolean", "default": False},
                "status": {"type": "string", "default": "backlog"},
            },
            "required": ["task_id", "title", "description", "owner"],
        },
    },
    {
        "name": "claim_task",
        "description": "Claim an available task in 'ready' status for execution by an authorized agent.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "Task ID to claim"},
                "agent": {"type": "string", "enum": ["coordinator", "backend_ml", "antigravity", "human"]},
            },
            "required": ["task_id", "agent"],
        },
    },
    {
        "name": "update_task",
        "description": "Update task progress, notes, or record modified files within declared scope.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "Task ID"},
                "agent": {"type": "string", "description": "Agent recording update"},
                "notes": {"type": "string", "description": "Progress note to append"},
                "files_changed": {"type": "array", "items": {"type": "string"}, "description": "List of changed files"},
            },
            "required": ["task_id", "agent"],
        },
    },
    {
        "name": "submit_for_review",
        "description": "Submit a verified task for coordinator review. Automatically generates the handoff report.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "Task ID"},
                "agent": {"type": "string", "description": "Executing agent name"},
                "summary": {"type": "string", "description": "Summary of work completed and evidence"},
            },
            "required": ["task_id", "agent"],
        },
    },
    {
        "name": "record_verification",
        "description": "Record an executed offline test command, its exit code, and output summary.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "Task ID"},
                "agent": {"type": "string", "description": "Agent that ran test"},
                "command": {"type": "string", "description": "Exact test command executed"},
                "exit_code": {"type": "integer", "description": "Exit code of test (0 for pass)"},
                "output_summary": {"type": "string", "description": "Test output excerpt (secrets redacted)"},
            },
            "required": ["task_id", "agent", "command", "exit_code"],
        },
    },
    {
        "name": "request_human_approval",
        "description": "Flag a task as requiring human intervention for sensitive operations or blockers.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "Task ID"},
                "requester": {"type": "string", "description": "Agent requesting approval"},
                "reason": {"type": "string", "description": "Specific reason human approval is needed"},
            },
            "required": ["task_id", "requester", "reason"],
        },
    },
    {
        "name": "get_project_status",
        "description": "Get high-level FieldIQ verified project status, environment specs, and active task board.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
]


def handle_tool_call(ledger: AgentTaskLedger, name: str, args: Dict[str, Any]) -> str:
    """Execute tool logic safely against the AgentTaskLedger."""
    if name == "list_tasks":
        tasks = ledger.list_tasks(status=args.get("status"), owner=args.get("owner"))
        summary = [
            {
                "task_id": t["task_id"],
                "title": t["title"],
                "owner": t["owner"],
                "status": t["status"],
                "priority": t["priority"],
                "approval_required": t.get("approval_required", False),
            }
            for t in tasks
        ]
        return json.dumps(summary, indent=2)

    elif name == "get_task":
        task = ledger.get_task(args["task_id"])
        return json.dumps(task, indent=2)

    elif name == "create_task":
        task = ledger.create_task(
            task_id=args["task_id"],
            title=args["title"],
            description=args["description"],
            owner=args["owner"],
            priority=args.get("priority", "medium"),
            allowed_files=args.get("allowed_files", []),
            forbidden_files=args.get("forbidden_files", []),
            dependencies=args.get("dependencies", []),
            acceptance_criteria=args.get("acceptance_criteria", []),
            verification_commands=args.get("verification_commands", []),
            approval_required=args.get("approval_required", False),
            status=args.get("status", "backlog"),
        )
        return json.dumps({"status": "created", "task": task}, indent=2)

    elif name == "claim_task":
        task = ledger.claim_task(args["task_id"], agent=args["agent"])
        return json.dumps({"status": "claimed", "task": task}, indent=2)

    elif name == "update_task":
        task_id = args["task_id"]
        agent = args["agent"]
        if args.get("files_changed"):
            ledger.record_changed_files(task_id, agent=agent, files=args["files_changed"])
        if args.get("notes"):
            data = ledger._read_data()
            task = next(t for t in data["tasks"] if t["task_id"] == task_id)
            task.setdefault("notes", []).append(f"[{ledger.get_utc_now_iso()}] {agent}: {args['notes']}")
            ledger._write_atomic(data)
        updated = ledger.get_task(task_id)
        return json.dumps({"status": "updated", "task": updated}, indent=2)

    elif name == "submit_for_review":
        task = ledger.submit_for_review(args["task_id"], agent=args["agent"], summary=args.get("summary", ""))
        return json.dumps({"status": "review_required", "task": task}, indent=2)

    elif name == "record_verification":
        task = ledger.record_test_results(
            task_id=args["task_id"],
            agent=args["agent"],
            command=args["command"],
            exit_code=args["exit_code"],
            output_summary=args.get("output_summary", ""),
        )
        return json.dumps({"status": "recorded", "task": task}, indent=2)

    elif name == "request_human_approval":
        task = ledger.request_human_approval(
            task_id=args["task_id"],
            requester=args["requester"],
            reason=args["reason"],
        )
        return json.dumps({"status": "approval_requested", "task": task}, indent=2)

    elif name == "get_project_status":
        tasks = ledger.list_tasks()
        status_counts = {}
        for t in tasks:
            s = t.get("status", "unknown")
            status_counts[s] = status_counts.get(s, 0) + 1
        summary = {
            "project": "FieldIQ",
            "coordination_ledger": str(ledger.ledger_path),
            "total_tasks": len(tasks),
            "task_breakdown": status_counts,
            "governing_policy": "AGENTS.md",
            "model_governance": "Model promotion requires explicit human approval; rejected models preserved.",
            "frontend_status": "Preserved for future integration; live server is not active during offline tests.",
        }
        return json.dumps(summary, indent=2)

    raise CoordinationError(f"Unknown tool name '{name}'.")


def run_stdio_server() -> None:
    """Run newline-delimited JSON-RPC 2.0 loop over stdin and stdout."""
    ledger = AgentTaskLedger()

    # Input reading loop
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        try:
            req = json.loads(line)
        except json.JSONDecodeError as err:
            err_resp = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": f"Parse error: {err}"},
            }
            sys.stdout.write(json.dumps(err_resp) + "\n")
            sys.stdout.flush()
            continue

        req_id = req.get("id")
        method = req.get("method")
        params = req.get("params", {})

        if method == "initialize":
            resp = {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
                },
            }
        elif method == "notifications/initialized":
            # Notification does not return a response
            continue
        elif method == "ping":
            resp = {"jsonrpc": "2.0", "id": req_id, "result": {}}
        elif method == "tools/list":
            resp = {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"tools": TOOLS},
            }
        elif method == "tools/call":
            tool_name = params.get("name")
            tool_args = params.get("arguments", {})
            try:
                result_text = handle_tool_call(ledger, tool_name, tool_args)
                resp = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": result_text}],
                        "isError": False,
                    },
                }
            except Exception as exc:
                resp = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": f"Coordination Error: {exc}"}],
                        "isError": True,
                    },
                }
        else:
            resp = {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Method '{method}' not found"},
            }

        sys.stdout.write(json.dumps(resp) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    run_stdio_server()
