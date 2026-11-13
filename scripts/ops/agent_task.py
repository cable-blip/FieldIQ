#!/usr/bin/env python3
"""
scripts/ops/agent_task.py
-------------------------
Command-line interface for the FieldIQ Agent Task Ledger and Coordination Bridge.

Usage Examples:
    python scripts/ops/agent_task.py list
    python scripts/ops/agent_task.py list --status ready
    python scripts/ops/agent_task.py claim FIQ-0001 --agent backend_ml
    python scripts/ops/agent_task.py verify FIQ-0001 --agent backend_ml
    python scripts/ops/agent_task.py approve FIQ-0001 --approver coordinator
    python scripts/ops/agent_task.py complete FIQ-0001 --agent coordinator
    python scripts/ops/agent_task.py history FIQ-0001
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.services.agent_coordination import (
    AgentTaskLedger,
    CoordinationError,
    redact_secrets,
)


def format_table(rows: list[list[str]], headers: list[str]) -> str:
    """Render a clean text table for terminal output."""
    all_rows = [headers] + rows
    col_widths = [max(len(str(r[i])) for r in all_rows) for i in range(len(headers))]
    
    header_line = " | ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers))
    sep_line = "-+-".join("-" * col_widths[i] for i in range(len(headers)))
    data_lines = [
        " | ".join(str(cell).ljust(col_widths[i]) for i, cell in enumerate(row))
        for row in rows
    ]
    return f"{header_line}\n{sep_line}\n" + "\n".join(data_lines)


def cmd_list(ledger: AgentTaskLedger, args: argparse.Namespace) -> int:
    tasks = ledger.list_tasks(status=args.status, owner=args.owner)
    if not tasks:
        print("No tasks found matching criteria.")
        return 0
    
    rows = []
    for t in tasks:
        rows.append([
            t["task_id"],
            t.get("title", "")[:35],
            t.get("owner", ""),
            t.get("status", ""),
            t.get("priority", ""),
            "Yes" if t.get("approval_required") else "No",
        ])
    print(format_table(rows, ["ID", "Title", "Owner", "Status", "Priority", "Approval Req"]))
    return 0


def cmd_create(ledger: AgentTaskLedger, args: argparse.Namespace) -> int:
    allowed = [f.strip() for f in args.allowed.split(",") if f.strip()] if args.allowed else []
    forbidden = [f.strip() for f in args.forbidden.split(",") if f.strip()] if args.forbidden else []
    criteria = [c.strip() for c in args.criteria.split(";") if c.strip()] if args.criteria else []
    commands = [cmd.strip() for cmd in args.commands.split(";") if cmd.strip()] if args.commands else []
    deps = [d.strip() for d in args.deps.split(",") if d.strip()] if args.deps else []

    try:
        task = ledger.create_task(
            task_id=args.task_id,
            title=args.title,
            description=args.desc,
            owner=args.owner,
            priority=args.priority,
            allowed_files=allowed,
            forbidden_files=forbidden,
            dependencies=deps,
            acceptance_criteria=criteria,
            verification_commands=commands,
            approval_required=args.approval_required,
            status=args.status or "backlog",
            creator=args.creator or "coordinator",
        )
        print(f"Task '{task['task_id']}' created successfully with status '{task['status']}'.")
        return 0
    except CoordinationError as err:
        print(f"Error creating task: {err}", file=sys.stderr)
        return 1


def cmd_claim(ledger: AgentTaskLedger, args: argparse.Namespace) -> int:
    try:
        task = ledger.claim_task(args.task_id, agent=args.agent)
        print(f"Task '{task['task_id']}' claimed by '{args.agent}'. Status is now '{task['status']}'.")
        return 0
    except CoordinationError as err:
        print(f"Error claiming task: {err}", file=sys.stderr)
        return 1


def cmd_release(ledger: AgentTaskLedger, args: argparse.Namespace) -> int:
    try:
        task = ledger.release_task(args.task_id, agent=args.agent, reason=args.reason or "")
        print(f"Task '{task['task_id']}' released by '{args.agent}'. Status is now '{task['status']}'.")
        return 0
    except CoordinationError as err:
        print(f"Error releasing task: {err}", file=sys.stderr)
        return 1


def cmd_block(ledger: AgentTaskLedger, args: argparse.Namespace) -> int:
    try:
        task = ledger.mark_blocked(args.task_id, agent=args.agent, blocker_description=args.reason)
        print(f"Task '{task['task_id']}' marked blocked by '{args.agent}'.")
        return 0
    except CoordinationError as err:
        print(f"Error blocking task: {err}", file=sys.stderr)
        return 1


def cmd_verify(ledger: AgentTaskLedger, args: argparse.Namespace) -> int:
    try:
        task = ledger.submit_for_verification(args.task_id, agent=args.agent)
        print(f"Task '{task['task_id']}' submitted for verification by '{args.agent}'.")
        return 0
    except CoordinationError as err:
        print(f"Error submitting for verification: {err}", file=sys.stderr)
        return 1


def cmd_approve(ledger: AgentTaskLedger, args: argparse.Namespace) -> int:
    try:
        task = ledger.approve_task(args.task_id, approver=args.approver, comment=args.comment or "")
        print(f"Task '{task['task_id']}' approved by '{args.approver}'.")
        return 0
    except CoordinationError as err:
        print(f"Error approving task: {err}", file=sys.stderr)
        return 1


def cmd_complete(ledger: AgentTaskLedger, args: argparse.Namespace) -> int:
    try:
        task = ledger.complete_task(args.task_id, agent=args.agent, comment=args.comment or "")
        print(f"Task '{task['task_id']}' completed by '{args.agent}'.")
        return 0
    except CoordinationError as err:
        print(f"Error completing task: {err}", file=sys.stderr)
        return 1


def cmd_history(ledger: AgentTaskLedger, args: argparse.Namespace) -> int:
    try:
        history = ledger.get_task_history(args.task_id)
        if not history:
            print(f"No history recorded for task '{args.task_id}'.")
            return 0
        print(f"=== Task History: {args.task_id} ===")
        for entry in history:
            ts = entry.get("timestamp", "N/A")
            act = entry.get("action", "")
            actor = entry.get("actor", "")
            details = entry.get("details", "")
            print(f"[{ts}] {act.upper()} by {actor}: {details}")
        return 0
    except CoordinationError as err:
        print(f"Error fetching history: {err}", file=sys.stderr)
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="FieldIQ Agent Task Coordination CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # list
    p_list = subparsers.add_parser("list", help="List tasks in ledger")
    p_list.add_argument("--status", help="Filter by status")
    p_list.add_argument("--owner", help="Filter by owner")

    # create
    p_create = subparsers.add_parser("create", help="Create new task")
    p_create.add_argument("task_id", help="Task ID (e.g. FIQ-0001)")
    p_create.add_argument("--title", required=True, help="Task title")
    p_create.add_argument("--desc", required=True, help="Task description")
    p_create.add_argument("--owner", required=True, help="Assigned owner")
    p_create.add_argument("--priority", default="medium", help="Priority (critical|high|medium|low)")
    p_create.add_argument("--allowed", help="Comma-separated allowed file paths/globs")
    p_create.add_argument("--forbidden", help="Comma-separated forbidden file paths/globs")
    p_create.add_argument("--criteria", help="Semicolon-separated acceptance criteria")
    p_create.add_argument("--commands", help="Semicolon-separated verification commands")
    p_create.add_argument("--deps", help="Comma-separated dependency task IDs")
    p_create.add_argument("--approval-required", action="store_true", help="Flag requiring human approval")
    p_create.add_argument("--status", default="backlog", help="Initial status")
    p_create.add_argument("--creator", default="coordinator", help="Task creator")

    # claim
    p_claim = subparsers.add_parser("claim", help="Claim a task")
    p_claim.add_argument("task_id", help="Task ID")
    p_claim.add_argument("--agent", required=True, help="Claiming agent name")

    # release
    p_release = subparsers.add_parser("release", help="Release a claimed task back to ready")
    p_release.add_argument("task_id", help="Task ID")
    p_release.add_argument("--agent", required=True, help="Releasing agent name")
    p_release.add_argument("--reason", help="Reason for release")

    # block
    p_block = subparsers.add_parser("block", help="Mark a task as blocked")
    p_block.add_argument("task_id", help="Task ID")
    p_block.add_argument("--agent", required=True, help="Agent reporting blocker")
    p_block.add_argument("--reason", required=True, help="Blocker details")

    # verify
    p_verify = subparsers.add_parser("verify", help="Submit task for verification")
    p_verify.add_argument("task_id", help="Task ID")
    p_verify.add_argument("--agent", default="backend_ml", help="Executing agent")

    # approve
    p_approve = subparsers.add_parser("approve", help="Approve verified task")
    p_approve.add_argument("task_id", help="Task ID")
    p_approve.add_argument("--approver", default="coordinator", help="Approver (coordinator|human)")
    p_approve.add_argument("--comment", help="Approval notes")

    # complete
    p_complete = subparsers.add_parser("complete", help="Complete an approved task")
    p_complete.add_argument("task_id", help="Task ID")
    p_complete.add_argument("--agent", default="coordinator", help="Completing agent")
    p_complete.add_argument("--comment", help="Completion notes")

    # history
    p_history = subparsers.add_parser("history", help="Show task history")
    p_history.add_argument("task_id", help="Task ID")

    args = parser.parse_args()
    ledger = AgentTaskLedger()

    handlers = {
        "list": cmd_list,
        "create": cmd_create,
        "claim": cmd_claim,
        "release": cmd_release,
        "block": cmd_block,
        "verify": cmd_verify,
        "approve": cmd_approve,
        "complete": cmd_complete,
        "history": cmd_history,
    }

    handler = handlers.get(args.command)
    if not handler:
        parser.print_help()
        return 1

    return handler(ledger, args)


if __name__ == "__main__":
    sys.exit(main())
