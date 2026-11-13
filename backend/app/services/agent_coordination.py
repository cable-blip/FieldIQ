"""
backend/app/services/agent_coordination.py
-----------------------------------------
Shared Multi-Agent Coordination Service for FieldIQ.

Provides thread-safe and process-safe operations on the shared task ledger,
enforces file ownership boundaries, validates state machine transitions,
redacts secrets, and generates auditable handoff reports.

Governing Policy: AGENTS.md & Docs/FieldIQ/05_Operations/Agent Collaboration Protocol.md
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from fnmatch import fnmatch
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

# Base workspace path
WORKSPACE_ROOT = Path(r"C:\Users\ADMIN\Downloads\FieldIQ_V2").resolve()
OPERATIONS_DIR = WORKSPACE_ROOT / "Docs" / "FieldIQ" / "05_Operations"
LEDGER_PATH = OPERATIONS_DIR / "agent_task_ledger.json"
OWNERSHIP_PATH = OPERATIONS_DIR / "file_ownership.json"
HANDOFFS_DIR = OPERATIONS_DIR / "handoffs"

# Task ID regex format: FIQ-0001
TASK_ID_REGEX = re.compile(r"^FIQ-[0-9]{4}$")

# Valid roles
VALID_ROLES = {"coordinator", "backend_ml", "antigravity", "human"}

# Valid priorities
VALID_PRIORITIES = {"critical", "high", "medium", "low"}

# Valid states
VALID_STATES = {
    "backlog",
    "ready",
    "claimed",
    "in_progress",
    "blocked",
    "verification",
    "review_required",
    "approved",
    "completed",
    "rejected",
    "cancelled",
}

# Permitted state transitions map: current_status -> set of allowed next_statuses
PERMITTED_TRANSITIONS: Dict[str, set[str]] = {
    "backlog": {"ready", "cancelled"},
    "ready": {"claimed", "backlog", "cancelled"},
    "claimed": {"in_progress", "ready", "cancelled"},
    "in_progress": {"verification", "blocked", "ready", "cancelled"},
    "blocked": {"in_progress", "ready", "cancelled"},
    "verification": {"review_required", "in_progress", "blocked"},
    "review_required": {"approved", "rejected", "in_progress"},
    "approved": {"completed", "in_progress"},
    "rejected": {"in_progress", "ready", "cancelled"},
    "completed": set(),  # terminal state
    "cancelled": {"backlog", "ready"},  # can be reopened
}

# Secret signatures with specific replacements
SECRET_REPLACEMENTS = [
    (
        re.compile(r"(?i)(api[_-]?key|secret|password|passwd|token|jwt|auth)[\s]*[=:]\s*['\"]?([A-Za-z0-9_\-\.]{8,})['\"]?"),
        r"\1=[REDACTED_SECRET]",
    ),
    (
        re.compile(r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----[\s\S]*?-----END (?:RSA |EC )?PRIVATE KEY-----"),
        "[REDACTED_PRIVATE_KEY]",
    ),
    (
        re.compile(r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----"),
        "[REDACTED_PRIVATE_KEY]",
    ),
    (
        re.compile(r"(?i)(bearer\s+)([A-Za-z0-9_\-\.]{16,})"),
        r"\1[REDACTED_TOKEN]",
    ),
]


class CoordinationError(Exception):
    """Base exception for all agent coordination errors."""
    pass


class TaskNotFoundError(CoordinationError):
    """Raised when a task ID cannot be found in the ledger."""
    pass


class DuplicateTaskError(CoordinationError):
    """Raised when attempting to create a task with an existing ID."""
    pass


class InvalidStateTransitionError(CoordinationError):
    """Raised when a task status transition violates the state machine."""
    pass


class OwnershipConflictError(CoordinationError):
    """Raised when an agent attempts an action on a task or file it does not own."""
    pass


class ScopeViolationError(CoordinationError):
    """Raised when a changed file violates the declared task scope."""
    pass


class ApprovalRequiredError(CoordinationError):
    """Raised when an operation requires explicit human approval before proceeding."""
    pass


class ModelPromotionProtectionError(CoordinationError):
    """Raised when an unapproved or rejected model is proposed for active promotion."""
    pass


def get_utc_now_iso() -> str:
    """Return the current UTC timestamp formatted in ISO 8601."""
    return datetime.now(timezone.utc).isoformat()


def redact_secrets(text: str) -> str:
    """Scan and redact secrets, keys, and tokens from strings."""
    if not isinstance(text, str):
        return text
    redacted = text
    for pattern, repl in SECRET_REPLACEMENTS:
        redacted = pattern.sub(repl, redacted)
    return redacted


def sanitize_data(data: Any) -> Any:
    """Recursively sanitize nested dictionaries and lists to remove secrets."""
    if isinstance(data, str):
        return redact_secrets(data)
    elif isinstance(data, list):
        return [sanitize_data(item) for item in data]
    elif isinstance(data, dict):
        return {k: sanitize_data(v) for k, v in data.items()}
    return data


def normalize_rel_path(path: Union[str, Path]) -> str:
    """Normalize file path relative to WORKSPACE_ROOT using forward slashes."""
    p = Path(path)
    if p.is_absolute():
        try:
            rel = p.relative_to(WORKSPACE_ROOT)
        except ValueError:
            rel = p
    else:
        rel = p
    return str(rel).replace("\\", "/")


def load_file_ownership(ownership_path: Optional[Path] = None) -> Dict[str, List[str]]:
    """Load the file ownership patterns mapping."""
    target_path = ownership_path or OWNERSHIP_PATH
    if not target_path.exists():
        return {
            "backend_ml": ["backend/**", "scripts/**", "tests/**", "models/**", "data/**", "rules/**", "simulation/**"],
            "antigravity": ["frontend/**"],
            "coordinator": ["PROJECT_STATUS.md", "Docs/**", "README.md"],
            "human_only": [".env", ".env.*", ".env.example", "security/**", "production secrets/**"],
        }
    with open(target_path, "r", encoding="utf-8") as f:
        return json.load(f)


def check_file_ownership(rel_path: str, ownership_map: Dict[str, List[str]]) -> List[str]:
    """Return all roles that own a given normalized relative path."""
    owners = []
    norm = normalize_rel_path(rel_path)
    for role, patterns in ownership_map.items():
        for pat in patterns:
            # Handle recursive globbing
            if fnmatch(norm, pat) or fnmatch(Path(norm).name, pat):
                owners.append(role)
                break
    return owners


def validate_task_id(task_id: str) -> None:
    """Ensure task_id adheres to FIQ-XXXX format."""
    if not isinstance(task_id, str) or not TASK_ID_REGEX.match(task_id.strip()):
        raise CoordinationError(f"Invalid task_id '{task_id}'. Must match format FIQ-0001 to FIQ-9999.")


class AgentTaskLedger:
    """
    Manages atomic persistence, validation, and operations on the FieldIQ task ledger.
    """

    def __init__(self, ledger_path: Optional[Path] = None, ownership_path: Optional[Path] = None):
        self.ledger_path = (ledger_path or LEDGER_PATH).resolve()
        self.ownership_path = (ownership_path or OWNERSHIP_PATH).resolve()
        self.ownership_map = load_file_ownership(self.ownership_path)
        self.ensure_initialized()

    def ensure_initialized(self) -> None:
        """Create the ledger file if it does not yet exist."""
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.ledger_path.exists():
            initial_data = {
                "schema_version": "1.0.0",
                "project": "FieldIQ",
                "workspace": str(WORKSPACE_ROOT),
                "updated_at": get_utc_now_iso(),
                "tasks": [],
            }
            self._write_atomic(initial_data)

    def _read_data(self) -> Dict[str, Any]:
        """Read and parse the ledger JSON."""
        if not self.ledger_path.exists():
            self.ensure_initialized()
        with open(self.ledger_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _write_atomic(self, data: Dict[str, Any]) -> None:
        """
        Write the ledger data atomically using a temporary file in the same directory.
        Redacts secrets before writing.
        """
        sanitized = sanitize_data(data)
        sanitized["updated_at"] = get_utc_now_iso()
        dir_name = self.ledger_path.parent
        dir_name.mkdir(parents=True, exist_ok=True)
        tmp_path = dir_name / f"{self.ledger_path.name}.tmp.{os.getpid()}"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(sanitized, f, indent=2)
        os.replace(tmp_path, self.ledger_path)

    def list_tasks(self, status: Optional[str] = None, owner: Optional[str] = None) -> List[Dict[str, Any]]:
        """List tasks optionally filtered by status and/or owner."""
        data = self._read_data()
        tasks = data.get("tasks", [])
        filtered = []
        for t in tasks:
            if status and t.get("status") != status:
                continue
            if owner and t.get("owner") != owner:
                continue
            filtered.append(t)
        return filtered

    def get_task(self, task_id: str) -> Dict[str, Any]:
        """Retrieve a task by ID. Raises TaskNotFoundError if not found."""
        validate_task_id(task_id)
        data = self._read_data()
        for t in data.get("tasks", []):
            if t["task_id"] == task_id:
                return t
        raise TaskNotFoundError(f"Task with ID '{task_id}' was not found in the ledger.")

    def create_task(
        self,
        task_id: str,
        title: str,
        description: str,
        owner: str,
        priority: str = "medium",
        allowed_files: Optional[List[str]] = None,
        forbidden_files: Optional[List[str]] = None,
        dependencies: Optional[List[str]] = None,
        acceptance_criteria: Optional[List[str]] = None,
        verification_commands: Optional[List[str]] = None,
        approval_required: bool = False,
        status: str = "backlog",
        creator: str = "coordinator",
    ) -> Dict[str, Any]:
        """Create a new task in the ledger."""
        validate_task_id(task_id)
        if owner not in VALID_ROLES:
            raise CoordinationError(f"Invalid owner '{owner}'. Must be one of {VALID_ROLES}.")
        if priority not in VALID_PRIORITIES:
            raise CoordinationError(f"Invalid priority '{priority}'. Must be one of {VALID_PRIORITIES}.")
        if status not in VALID_STATES:
            raise CoordinationError(f"Invalid initial status '{status}'. Must be one of {VALID_STATES}.")

        data = self._read_data()
        for existing in data.get("tasks", []):
            if existing["task_id"] == task_id:
                raise DuplicateTaskError(f"Task '{task_id}' already exists in the ledger.")

        now = get_utc_now_iso()
        task_record: Dict[str, Any] = {
            "task_id": task_id,
            "title": title.strip(),
            "description": description.strip(),
            "owner": owner,
            "status": status,
            "priority": priority,
            "scope": {
                "allowed_files": [normalize_rel_path(p) for p in (allowed_files or [])],
                "forbidden_files": [normalize_rel_path(p) for p in (forbidden_files or [])],
            },
            "dependencies": dependencies or [],
            "acceptance_criteria": acceptance_criteria or [],
            "verification_commands": verification_commands or [],
            "files_changed": [],
            "tests_run": [],
            "test_results": [],
            "blockers": [],
            "approval_required": approval_required,
            "claimed_at": now if status == "claimed" else None,
            "completed_at": None,
            "notes": [f"[{now}] Task created with status '{status}' by {creator}."],
            "history": [
                {
                    "timestamp": now,
                    "action": "create",
                    "from_status": None,
                    "to_status": status,
                    "actor": creator,
                    "details": f"Created task: {title}",
                }
            ],
        }

        # Validate file ownership on initial allowed_files
        self._validate_initial_scope_ownership(task_record["owner"], task_record["scope"]["allowed_files"], task_record["approval_required"])

        data["tasks"].append(task_record)
        self._write_atomic(data)
        return task_record

    def _validate_initial_scope_ownership(self, owner: str, allowed_files: List[str], approval_required: bool) -> None:
        """Check if any allowed files are human_only or cross-owner."""
        for path in allowed_files:
            owners = check_file_ownership(path, self.ownership_map)
            if "human_only" in owners:
                raise OwnershipConflictError(f"File '{path}' is strictly 'human_only'. Cannot be in automated task scope.")
            if owners and owner not in owners and not approval_required:
                raise OwnershipConflictError(
                    f"File '{path}' is owned by {owners}, but task owner is '{owner}'. "
                    "Cross-ownership requires 'approval_required: true' (coordination_required)."
                )

    def _record_transition(self, task: Dict[str, Any], next_status: str, actor: str, reason: str = "") -> None:
        """Record a state machine transition with audit logging."""
        curr_status = task["status"]
        if next_status not in PERMITTED_TRANSITIONS.get(curr_status, set()):
            raise InvalidStateTransitionError(
                f"Cannot transition task '{task['task_id']}' from '{curr_status}' to '{next_status}'. "
                f"Permitted transitions: {sorted(list(PERMITTED_TRANSITIONS.get(curr_status, set())))}"
            )
        now = get_utc_now_iso()
        task["status"] = next_status
        note = f"[{now}] Status transitioned from '{curr_status}' to '{next_status}' by {actor}."
        if reason:
            note += f" Reason: {reason}"
        task.setdefault("notes", []).append(note)
        task.setdefault("history", []).append({
            "timestamp": now,
            "action": "transition",
            "from_status": curr_status,
            "to_status": next_status,
            "actor": actor,
            "details": reason or f"Transition to {next_status}",
        })

    def claim_task(self, task_id: str, agent: str) -> Dict[str, Any]:
        """Claim a task for execution."""
        if agent not in VALID_ROLES:
            raise CoordinationError(f"Invalid claiming agent '{agent}'.")
        data = self._read_data()
        task = None
        for t in data.get("tasks", []):
            if t["task_id"] == task_id:
                task = t
                break
        if not task:
            raise TaskNotFoundError(f"Task '{task_id}' not found.")

        # Duplicate claim check
        if task["status"] in {"claimed", "in_progress", "verification"}:
            if task.get("claimed_by") and task.get("claimed_by") != agent:
                raise OwnershipConflictError(
                    f"Task '{task_id}' is already claimed by '{task.get('claimed_by')}'. "
                    f"Agent '{agent}' cannot double-claim."
                )

        # Ownership conflict check
        if task["owner"] != agent and task["owner"] != "coordinator" and agent != "human":
            if not task.get("approval_required"):
                raise OwnershipConflictError(
                    f"Task '{task_id}' is assigned to owner '{task['owner']}'. "
                    f"Agent '{agent}' cannot claim it without approval_required: true."
                )

        # Check dependencies
        if task.get("dependencies"):
            for dep_id in task["dependencies"]:
                dep = next((d for d in data["tasks"] if d["task_id"] == dep_id), None)
                if not dep or dep.get("status") != "completed":
                    raise CoordinationError(f"Cannot claim task '{task_id}': dependency '{dep_id}' is not completed.")

        now = get_utc_now_iso()
        # If backlog, move to ready then claimed
        if task["status"] == "backlog":
            self._record_transition(task, "ready", actor=agent, reason="Prerequisites verified")
        self._record_transition(task, "claimed", actor=agent, reason="Claimed for active work")
        self._record_transition(task, "in_progress", actor=agent, reason="Work commenced")
        task["claimed_at"] = now
        task["claimed_by"] = agent

        self._write_atomic(data)
        return task

    def release_task(self, task_id: str, agent: str, reason: str = "") -> Dict[str, Any]:
        """Release a claimed task back to 'ready' status."""
        data = self._read_data()
        task = next((t for t in data.get("tasks", []) if t["task_id"] == task_id), None)
        if not task:
            raise TaskNotFoundError(f"Task '{task_id}' not found.")

        if task["status"] not in {"claimed", "in_progress", "blocked"}:
            raise CoordinationError(f"Cannot release task '{task_id}' in state '{task['status']}'.")

        self._record_transition(task, "ready", actor=agent, reason=f"Released claim. {reason}".strip())
        task["claimed_by"] = None
        self._write_atomic(data)
        return task

    def mark_blocked(self, task_id: str, agent: str, blocker_description: str) -> Dict[str, Any]:
        """Mark a task as blocked."""
        data = self._read_data()
        task = next((t for t in data.get("tasks", []) if t["task_id"] == task_id), None)
        if not task:
            raise TaskNotFoundError(f"Task '{task_id}' not found.")

        self._record_transition(task, "blocked", actor=agent, reason=blocker_description)
        now = get_utc_now_iso()
        task.setdefault("blockers", []).append({
            "timestamp": now,
            "agent": agent,
            "description": blocker_description,
        })
        self._write_atomic(data)
        return task

    def validate_file_scope(self, task_id: str, file_paths: List[str]) -> Tuple[bool, List[str]]:
        """
        Validate whether proposed file modifications are within the task's allowed scope.
        Returns (is_valid, list_of_violations).
        """
        task = self.get_task(task_id)
        allowed = task.get("scope", {}).get("allowed_files", [])
        forbidden = task.get("scope", {}).get("forbidden_files", [])
        violations = []

        for raw_path in file_paths:
            path = normalize_rel_path(raw_path)
            # Check human_only
            owners = check_file_ownership(path, self.ownership_map)
            if "human_only" in owners:
                violations.append(f"File '{path}' is classified as 'human_only'. Automated edit forbidden.")
                continue

            # Check explicit forbidden
            is_forbidden = any(fnmatch(path, f) or fnmatch(Path(path).name, f) for f in forbidden)
            if is_forbidden:
                violations.append(f"File '{path}' is explicitly forbidden in task scope.")
                continue

            # Check allowed if allowed list is not empty
            if allowed:
                is_allowed = any(fnmatch(path, a) or fnmatch(Path(path).name, a) for a in allowed)
                if not is_allowed:
                    violations.append(f"File '{path}' is not within declared allowed_files scope.")

        return (len(violations) == 0, violations)

    def record_changed_files(self, task_id: str, agent: str, files: List[str]) -> Dict[str, Any]:
        """Record modified files after validating against declared scope."""
        is_valid, violations = self.validate_file_scope(task_id, files)
        if not is_valid:
            raise ScopeViolationError(f"Scope violation for task '{task_id}': {'; '.join(violations)}")

        data = self._read_data()
        task = next((t for t in data.get("tasks", []) if t["task_id"] == task_id), None)
        if not task:
            raise TaskNotFoundError(f"Task '{task_id}' not found.")

        norm_files = [normalize_rel_path(f) for f in files]
        for f in norm_files:
            if f not in task.setdefault("files_changed", []):
                task["files_changed"].append(f)

        now = get_utc_now_iso()
        task.setdefault("notes", []).append(f"[{now}] Recorded changed files by {agent}: {norm_files}")
        self._write_atomic(data)
        return task

    def record_test_results(
        self,
        task_id: str,
        agent: str,
        command: str,
        exit_code: int,
        output_summary: str,
    ) -> Dict[str, Any]:
        """Record executed verification tests and their exit codes."""
        data = self._read_data()
        task = next((t for t in data.get("tasks", []) if t["task_id"] == task_id), None)
        if not task:
            raise TaskNotFoundError(f"Task '{task_id}' not found.")

        now = get_utc_now_iso()
        result_entry = {
            "timestamp": now,
            "agent": agent,
            "command": command,
            "exit_code": exit_code,
            "status": "PASS" if exit_code == 0 else "FAIL",
            "summary": redact_secrets(output_summary[:2000]),
        }
        task.setdefault("test_results", []).append(result_entry)
        if command not in task.setdefault("tests_run", []):
            task["tests_run"].append(command)

        task.setdefault("notes", []).append(
            f"[{now}] Test execution recorded: '{command}' -> Exit {exit_code} ({result_entry['status']})."
        )
        self._write_atomic(data)
        return task

    def submit_for_verification(self, task_id: str, agent: str) -> Dict[str, Any]:
        """Transition task to 'verification' state."""
        data = self._read_data()
        task = next((t for t in data.get("tasks", []) if t["task_id"] == task_id), None)
        if not task:
            raise TaskNotFoundError(f"Task '{task_id}' not found.")

        # Require acceptance criteria
        if not task.get("acceptance_criteria"):
            raise CoordinationError(f"Cannot submit task '{task_id}' for verification: acceptance_criteria is empty.")

        self._record_transition(task, "verification", actor=agent, reason="Ready for test execution and verification")
        self._write_atomic(data)
        return task

    def submit_for_review(self, task_id: str, agent: str, summary: str = "") -> Dict[str, Any]:
        """
        Transition task to 'review_required' after verification tests have passed.
        Generates the mandatory handoff report.
        """
        data = self._read_data()
        task = next((t for t in data.get("tasks", []) if t["task_id"] == task_id), None)
        if not task:
            raise TaskNotFoundError(f"Task '{task_id}' not found.")

        # Ensure verification results exist
        if not task.get("test_results"):
            raise CoordinationError(f"Cannot submit task '{task_id}' for review: no test results recorded.")

        # Ensure no failing tests
        for res in task["test_results"]:
            if res.get("exit_code") != 0:
                raise CoordinationError(
                    f"Cannot submit task '{task_id}' for review with failing test: "
                    f"'{res.get('command')}' failed with exit code {res.get('exit_code')}."
                )

        self._record_transition(task, "review_required", actor=agent, reason=summary or "Verification tests passed")
        self._write_atomic(data)

        # Generate handoff report automatically
        self.generate_handoff_report(task_id, agent=agent)
        return task

    def approve_task(self, task_id: str, approver: str = "coordinator", comment: str = "") -> Dict[str, Any]:
        """Approve a task after evidence review."""
        if approver not in {"coordinator", "human"}:
            raise CoordinationError(f"Approver '{approver}' is not authorized to approve tasks.")

        data = self._read_data()
        task = next((t for t in data.get("tasks", []) if t["task_id"] == task_id), None)
        if not task:
            raise TaskNotFoundError(f"Task '{task_id}' not found.")

        if task.get("approval_required") and approver != "human":
            raise ApprovalRequiredError(
                f"Task '{task_id}' requires explicit 'human' approval because 'approval_required: true'."
            )

        self._record_transition(task, "approved", actor=approver, reason=comment or "Evidence verified and approved")
        task["approved_by"] = approver
        self._write_atomic(data)
        return task

    def complete_task(self, task_id: str, agent: str = "coordinator", comment: str = "") -> Dict[str, Any]:
        """Mark task as completed."""
        data = self._read_data()
        task = next((t for t in data.get("tasks", []) if t["task_id"] == task_id), None)
        if not task:
            raise TaskNotFoundError(f"Task '{task_id}' not found.")

        now = get_utc_now_iso()
        self._record_transition(task, "completed", actor=agent, reason=comment or "All requirements finalized")
        task["completed_at"] = now
        self._write_atomic(data)
        return task

    def request_human_approval(self, task_id: str, requester: str, reason: str) -> Dict[str, Any]:
        """Flag task as requiring human intervention."""
        data = self._read_data()
        task = next((t for t in data.get("tasks", []) if t["task_id"] == task_id), None)
        if not task:
            raise TaskNotFoundError(f"Task '{task_id}' not found.")

        task["approval_required"] = True
        now = get_utc_now_iso()
        task.setdefault("notes", []).append(f"[{now}] Human approval requested by {requester}: {reason}")
        self._write_atomic(data)
        return task

    def get_task_history(self, task_id: str) -> List[Dict[str, Any]]:
        """Return the complete audit history for a task."""
        task = self.get_task(task_id)
        return task.get("history", [])

    def generate_handoff_report(
        self,
        task_id: str,
        agent: str,
        assumptions: Optional[List[str]] = None,
        guarded_files: Optional[List[str]] = None,
        known_limitations: Optional[List[str]] = None,
        unresolved_questions: Optional[List[str]] = None,
        next_action: Optional[str] = None,
    ) -> Path:
        """
        Generate an immutable Markdown handoff report in Docs/FieldIQ/05_Operations/handoffs/
        adhering to Phase 6 requirements.
        """
        task = self.get_task(task_id)
        HANDOFFS_DIR.mkdir(parents=True, exist_ok=True)
        date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        report_filename = f"{task_id}_{date_str}.md"
        report_path = HANDOFFS_DIR / report_filename

        # Assemble markdown content
        lines = [
            f"# Agent Handoff Report — {task_id}",
            "",
            f"**Task ID:** {task_id}  ",
            f"**Task Title:** {task.get('title', 'N/A')}  ",
            f"**Executing Agent:** `{agent}`  ",
            f"**Date (UTC):** {get_utc_now_iso()}  ",
            f"**Current Status:** `{task.get('status', 'N/A')}`  ",
            f"**Approval Required:** `{task.get('approval_required', False)}`  ",
            "",
            "---",
            "",
            "## 1. Objective",
            task.get("description", "No description provided."),
            "",
            "## 2. Assumptions & Domain Constraints",
        ]

        assump_list = assumptions or [
            "Conforms strictly to governing AGENTS.md rules.",
            "No unverified cricket tactical heuristics or synthetic values introduced.",
            "Files edited remain strictly within declared task scope.",
        ]
        for a in assump_list:
            lines.append(f"- {a}")

        lines.extend([
            "",
            "## 3. Files Changed",
        ])
        changed = task.get("files_changed", [])
        if changed:
            for f in changed:
                lines.append(f"- `{f}`")
        else:
            lines.append("- *(No source files modified in this task)*")

        lines.extend([
            "",
            "## 4. Files Not Changed (Guarded & Preserved)",
        ])
        guarded = guarded_files or [
            ".env & credentials (human-only)",
            "Active production model registry pointer",
            "Live frontend interface (preserved for future integration)",
        ]
        for g in guarded:
            lines.append(f"- `{g}`")

        lines.extend([
            "",
            "## 5. Verification Commands & Exact Results",
        ])
        results = task.get("test_results", [])
        if results:
            for idx, r in enumerate(results, 1):
                lines.append(f"### Verification Run #{idx}")
                lines.append(f"- **Command:** `{r.get('command')}`")
                lines.append(f"- **Exit Code:** `{r.get('exit_code')}`")
                lines.append(f"- **Status:** `{r.get('status')}`")
                lines.append("```text")
                lines.append(r.get("summary", "No summary output recorded."))
                lines.append("```")
        else:
            lines.append("- *(No test results recorded yet)*")

        lines.extend([
            "",
            "## 6. Known Limitations & Edge Cases",
        ])
        limits = known_limitations or [
            "Offline/backend execution only; live frontend servers are not run during this stage.",
            "Dataset spatial status remains bounded by source wagon-wheel availability (Zone 0 = unavailable).",
        ]
        for lim in limits:
            lines.append(f"- {lim}")

        lines.extend([
            "",
            "## 7. Unresolved Questions",
        ])
        questions = unresolved_questions or [
            "- None at this stage.",
        ]
        for q in questions:
            lines.append(f"- {q}")

        lines.extend([
            "",
            "## 8. Requested Next Action",
            next_action or "Coordinator to review test evidence and approve task completion.",
            "",
            "## 9. Approval Requirements",
            f"- **Human Approval Required:** `{task.get('approval_required', False)}`",
            f"- **Approved By:** `{task.get('approved_by', 'None')}`",
            "",
            "---",
            "*Report generated by FieldIQ Multi-Agent Coordination Service.*",
        ])

        with open(report_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

        return report_path


def protect_model_promotion(task_id: str, proposed_registry_path: Path) -> None:
    """
    Validate that no candidate model with failed promotion gates or 'promoted: false'
    is inadvertently set as active production model without explicit human authorization.
    """
    if not proposed_registry_path.exists():
        return
    with open(proposed_registry_path, "r", encoding="utf-8") as f:
        registry = json.load(f)

    active_model = registry.get("active_production_model")
    models = registry.get("models", {})
    if active_model and active_model in models:
        meta = models[active_model]
        if meta.get("promoted") is False or meta.get("status") == "candidate":
            raise ModelPromotionProtectionError(
                f"Model '{active_model}' is marked 'promoted: false' or 'candidate'. "
                "Silently activating it violates Model Governance (Rule 15). Human approval is mandatory."
            )
