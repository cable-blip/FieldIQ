"""
tests/test_agent_coordination.py
---------------------------------
Comprehensive verification test suite for the FieldIQ Agent Collaboration Bridge.

Covers all Phase 10 requirements:
  - task creation
  - duplicate task rejection
  - task claiming
  - ownership conflicts
  - invalid task transitions
  - atomic ledger writes
  - file-scope validation
  - missing acceptance criteria
  - missing verification results
  - human-approval enforcement
  - rejected-model protection
  - secret redaction
  - handoff report generation

Offline test suite: zero network calls, zero server spawns, zero browser dependencies.
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from backend.app.services.agent_coordination import (
    AgentTaskLedger,
    CoordinationError,
    DuplicateTaskError,
    InvalidStateTransitionError,
    OwnershipConflictError,
    ScopeViolationError,
    ApprovalRequiredError,
    ModelPromotionProtectionError,
    redact_secrets,
    protect_model_promotion,
    validate_task_id,
)


@pytest.fixture
def temp_ledger(tmp_path: Path):
    """Create an isolated AgentTaskLedger instance in a temporary directory."""
    ledger_file = tmp_path / "test_ledger.json"
    ownership_file = tmp_path / "test_ownership.json"
    
    ownership_data = {
        "backend_ml": ["backend/**", "scripts/**", "tests/**", "models/**", "data/**"],
        "antigravity": ["frontend/**"],
        "coordinator": ["PROJECT_STATUS.md", "Docs/**", "README.md"],
        "human_only": [".env", ".env.*", "security/**", "production secrets/**"]
    }
    with open(ownership_file, "w", encoding="utf-8") as f:
        json.dump(ownership_data, f)
        
    ledger = AgentTaskLedger(ledger_path=ledger_file, ownership_path=ownership_file)
    return ledger


# 1. Task Creation
def test_task_creation_valid(temp_ledger: AgentTaskLedger):
    task = temp_ledger.create_task(
        task_id="FIQ-1001",
        title="Sample Test Task",
        description="Verify task creation mechanics.",
        owner="backend_ml",
        priority="high",
        allowed_files=["backend/app/services/metrics.py"],
        acceptance_criteria=["Criteria 1"],
        verification_commands=["python -m pytest tests/"],
        status="ready",
    )
    assert task["task_id"] == "FIQ-1001"
    assert task["title"] == "Sample Test Task"
    assert task["status"] == "ready"
    assert task["owner"] == "backend_ml"
    assert len(task["history"]) >= 1
    assert task["scope"]["allowed_files"] == ["backend/app/services/metrics.py"]


# 2. Duplicate Task Rejection
def test_duplicate_task_rejection(temp_ledger: AgentTaskLedger):
    temp_ledger.create_task(
        task_id="FIQ-1002",
        title="Task 1",
        description="First instance",
        owner="backend_ml",
    )
    with pytest.raises(DuplicateTaskError, match="already exists"):
        temp_ledger.create_task(
            task_id="FIQ-1002",
            title="Task 1 Duplicate",
            description="Second instance with same ID",
            owner="backend_ml",
        )


# 3. Task Claiming
def test_task_claiming_lifecycle(temp_ledger: AgentTaskLedger):
    temp_ledger.create_task(
        task_id="FIQ-1003",
        title="Claimable Task",
        description="Work to be claimed",
        owner="backend_ml",
        status="ready",
    )
    claimed = temp_ledger.claim_task("FIQ-1003", agent="backend_ml")
    assert claimed["status"] == "in_progress"
    assert claimed["claimed_by"] == "backend_ml"
    assert claimed["claimed_at"] is not None


# 4. Ownership Conflicts (Double Claiming & Cross-Agent Claims)
def test_ownership_conflicts_double_claim(temp_ledger: AgentTaskLedger):
    temp_ledger.create_task(
        task_id="FIQ-1004",
        title="Double Claim Test",
        description="Test mutual exclusion",
        owner="backend_ml",
        status="ready",
    )
    temp_ledger.claim_task("FIQ-1004", agent="backend_ml")
    
    with pytest.raises(OwnershipConflictError, match="already claimed"):
        temp_ledger.claim_task("FIQ-1004", agent="antigravity")


def test_ownership_conflicts_unassigned_agent(temp_ledger: AgentTaskLedger):
    temp_ledger.create_task(
        task_id="FIQ-1005",
        title="Backend Owned Task",
        description="Assigned strictly to backend_ml",
        owner="backend_ml",
        approval_required=False,
        status="ready",
    )
    with pytest.raises(OwnershipConflictError, match="assigned to owner 'backend_ml'"):
        temp_ledger.claim_task("FIQ-1005", agent="antigravity")


# 5. Invalid Task Transitions
def test_invalid_task_transitions(temp_ledger: AgentTaskLedger):
    temp_ledger.create_task(
        task_id="FIQ-1006",
        title="Transition Test",
        description="Test state machine boundaries",
        owner="backend_ml",
        status="backlog",
    )
    with pytest.raises(InvalidStateTransitionError, match="Cannot transition task"):
        # Cannot jump from backlog directly to completed
        temp_ledger.complete_task("FIQ-1006", agent="coordinator")


# 6. Atomic Ledger Writes
def test_atomic_ledger_writes(temp_ledger: AgentTaskLedger):
    initial_data = temp_ledger._read_data()
    temp_ledger.create_task(
        task_id="FIQ-1007",
        title="Atomic Test",
        description="Verify atomic persistence",
        owner="coordinator",
    )
    updated_data = temp_ledger._read_data()
    assert len(updated_data["tasks"]) == len(initial_data["tasks"]) + 1
    assert temp_ledger.ledger_path.exists()
    # Ensure no lingering temp files in directory
    temp_files = list(temp_ledger.ledger_path.parent.glob("*.tmp.*"))
    assert len(temp_files) == 0


# 7. File-Scope Validation
def test_file_scope_validation_success_and_failure(temp_ledger: AgentTaskLedger):
    temp_ledger.create_task(
        task_id="FIQ-1008",
        title="Scoped Work",
        description="Test file scope boundaries",
        owner="backend_ml",
        allowed_files=["backend/app/services/metrics.py", "scripts/train/**"],
        forbidden_files=["tests/test_route_security.py"],
        status="ready",
    )
    temp_ledger.claim_task("FIQ-1008", agent="backend_ml")

    # Valid change
    task = temp_ledger.record_changed_files("FIQ-1008", agent="backend_ml", files=["backend/app/services/metrics.py"])
    assert "backend/app/services/metrics.py" in task["files_changed"]

    # Forbidden change
    with pytest.raises(ScopeViolationError, match="Scope violation"):
        temp_ledger.record_changed_files("FIQ-1008", agent="backend_ml", files=["tests/test_route_security.py"])

    # Human-only file attempt
    with pytest.raises(ScopeViolationError, match="human_only"):
        temp_ledger.record_changed_files("FIQ-1008", agent="backend_ml", files=[".env"])


# 8. Missing Acceptance Criteria Check
def test_missing_acceptance_criteria_blocks_verification(temp_ledger: AgentTaskLedger):
    temp_ledger.create_task(
        task_id="FIQ-1009",
        title="No Criteria Task",
        description="Missing criteria",
        owner="backend_ml",
        acceptance_criteria=[],
        status="ready",
    )
    temp_ledger.claim_task("FIQ-1009", agent="backend_ml")
    with pytest.raises(CoordinationError, match="acceptance_criteria is empty"):
        temp_ledger.submit_for_verification("FIQ-1009", agent="backend_ml")


# 9. Missing Verification Results Check
def test_missing_verification_results_blocks_review(temp_ledger: AgentTaskLedger):
    temp_ledger.create_task(
        task_id="FIQ-1010",
        title="Unverified Task",
        description="No test results recorded",
        owner="backend_ml",
        acceptance_criteria=["Criteria present"],
        status="ready",
    )
    temp_ledger.claim_task("FIQ-1010", agent="backend_ml")
    temp_ledger.submit_for_verification("FIQ-1010", agent="backend_ml")

    # Attempt submit for review with zero tests
    with pytest.raises(CoordinationError, match="no test results recorded"):
        temp_ledger.submit_for_review("FIQ-1010", agent="backend_ml")

    # Record failing test
    temp_ledger.record_test_results("FIQ-1010", agent="backend_ml", command="pytest", exit_code=1, output_summary="FAILED")
    with pytest.raises(CoordinationError, match="failing test"):
        temp_ledger.submit_for_review("FIQ-1010", agent="backend_ml")


# 10. Human-Approval Enforcement
def test_human_approval_enforcement(temp_ledger: AgentTaskLedger):
    temp_ledger.create_task(
        task_id="FIQ-1011",
        title="Sensitive Arch Change",
        description="Requires human signoff",
        owner="backend_ml",
        acceptance_criteria=["Criteria"],
        approval_required=True,
        status="ready",
    )
    temp_ledger.claim_task("FIQ-1011", agent="backend_ml")
    temp_ledger.submit_for_verification("FIQ-1011", agent="backend_ml")
    temp_ledger.record_test_results("FIQ-1011", agent="backend_ml", command="pytest", exit_code=0, output_summary="PASS")
    temp_ledger.submit_for_review("FIQ-1011", agent="backend_ml")

    # Attempt approval by coordinator must fail
    with pytest.raises(ApprovalRequiredError, match="requires explicit 'human' approval"):
        temp_ledger.approve_task("FIQ-1011", approver="coordinator")

    # Human approval succeeds
    approved = temp_ledger.approve_task("FIQ-1011", approver="human", comment="Approved by system architect")
    assert approved["status"] == "approved"
    assert approved["approved_by"] == "human"


# 11. Rejected-Model Protection
def test_rejected_model_protection(tmp_path: Path):
    reg_file = tmp_path / "model_registry.json"
    registry_data = {
        "active_production_model": "xgboost_v3_uncalibrated",
        "models": {
            "xgboost_v3_uncalibrated": {
                "status": "candidate",
                "promoted": False,
                "promotion_gates": {
                    "gate_1_wicket_recall": "FAILED"
                }
            }
        }
    }
    with open(reg_file, "w", encoding="utf-8") as f:
        json.dump(registry_data, f)

    with pytest.raises(ModelPromotionProtectionError, match="violates Model Governance"):
        protect_model_promotion("FIQ-0004", reg_file)


# 12. Secret Redaction
def test_secret_redaction():
    text_with_key = "Connecting to DB with api_key=ab39d8f92147ae82c0 and jwt_secret=xyzSecret9988."
    redacted = redact_secrets(text_with_key)
    assert "ab39d8f92147ae82c0" not in redacted
    assert "xyzSecret9988" not in redacted
    assert "api_key=[REDACTED_SECRET]" in redacted

    cert_text = "-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASC\n-----END PRIVATE KEY-----"
    redacted_cert = redact_secrets(cert_text)
    assert "[REDACTED_PRIVATE_KEY]" in redacted_cert


# 13. Handoff Report Generation
def test_handoff_report_generation(temp_ledger: AgentTaskLedger):
    temp_ledger.create_task(
        task_id="FIQ-1012",
        title="Report Generation Test",
        description="Verify handoff markdown report generation",
        owner="backend_ml",
        acceptance_criteria=["Criteria"],
        status="ready",
    )
    temp_ledger.claim_task("FIQ-1012", agent="backend_ml")
    temp_ledger.record_changed_files("FIQ-1012", agent="backend_ml", files=["backend/app/services/metrics.py"])
    temp_ledger.submit_for_verification("FIQ-1012", agent="backend_ml")
    temp_ledger.record_test_results("FIQ-1012", agent="backend_ml", command="pytest tests/", exit_code=0, output_summary="91 passed")
    temp_ledger.submit_for_review("FIQ-1012", agent="backend_ml")

    report_path = temp_ledger.generate_handoff_report("FIQ-1012", agent="backend_ml")
    assert report_path.exists()
    content = report_path.read_text(encoding="utf-8")
    
    # Check all required sections
    assert "# Agent Handoff Report — FIQ-1012" in content
    assert "## 1. Objective" in content
    assert "## 2. Assumptions & Domain Constraints" in content
    assert "## 3. Files Changed" in content
    assert "## 4. Files Not Changed" in content
    assert "## 5. Verification Commands & Exact Results" in content
    assert "## 6. Known Limitations & Edge Cases" in content
    assert "## 7. Unresolved Questions" in content
    assert "## 8. Requested Next Action" in content
    assert "## 9. Approval Requirements" in content
    assert "91 passed" in content
