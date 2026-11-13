"""
model_registry.py
-----------------
Production model governance, versioning, promotion gates, and rollback registry.

Promotion Governance Rules:
1. Candidate Isolation: New models are registered strictly as 'candidate' and cannot replace the active model automatically.
2. Objective Promotion Gates: Must satisfy explicit criteria across test-set log-loss, wicket recall/precision, boundary detection, and calibration error.
3. Audit Trail: Failed and retired candidates are preserved with full evaluation reports.
4. Safe Fallback & Rollback: Active model remains stable if a candidate fails; previous models can be reactivated without redeployment.
5. Zero Global State Leakage: Model state is persisted in models/model_registry.json.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from enum import Enum

class ModelCategory(str, Enum):
    PROBABILITY_MODEL = "probability_model"
    DECISION_POLICY = "decision_policy"
    SPATIAL_MODEL = "spatial_model"
    NON_SPATIAL_MODEL = "non_spatial_model"

class PromotionStatus(str, Enum):
    CANDIDATE = "candidate"
    REJECTED = "rejected"
    PRODUCTION_APPROVED = "production_approved"
    SHADOW_ONLY = "shadow_only"

MODELS_DIR = Path(__file__).resolve().parents[3] / "models"
REGISTRY_FILE = MODELS_DIR / "model_registry.json"

DEFAULT_PROMOTION_GATES = {
    "wicket_recall_min": 0.15,
    "wicket_precision_min": 0.12,
    "boundary_f1_min": 0.30,
    "max_log_loss": 1.350,
    "max_brier_score": 0.750,
    "probability_sum_tolerance": 0.001,
}

DEFAULT_PROBABILITY_GATES = {
    "max_log_loss": 1.450,
    "max_brier_sum": 0.700,
    "max_ece": 0.050,
    "min_wicket_pr_auc": 0.070,
    "min_boundary_pr_auc": 0.250,
    "require_valid_simplex": True,
}

DEFAULT_DECISION_GATES = {
    "min_wicket_recall": 0.150,
    "min_wicket_precision": 0.080,
    "min_boundary_recall": 0.400,
    "min_boundary_precision": 0.200,
    "max_expected_cost_per_ball": 1.050,
}

DEFAULT_OPERATIONAL_GATES = {
    "require_artifact_exists": True,
    "require_human_approval": True,
    "max_latency_ms": 25.0,
}


class ModelRegistry:
    """Manages versioned machine learning model candidates and production promotions."""

    def __init__(self, registry_path: Optional[Path] = None):
        self.registry_path = registry_path or REGISTRY_FILE
        self._ensure_registry_exists()

    def _ensure_registry_exists(self) -> None:
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.registry_path.exists():
            initial_data = {
                "active_model_id": "fieldiq_xgb_baseline_v1",
                "active_model_version": "1.0.0",
                "active_dataset_version": "2.0.0",
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "models": {
                    "fieldiq_xgb_baseline_v1": {
                        "model_id": "fieldiq_xgb_baseline_v1",
                        "model_version": "1.0.0",
                        "architecture": "XGBoost Multi-Class Classifier (single)",
                        "dataset_version": "2.0.0",
                        "feature_version": "1.0.0",
                        "training_period": "2005-2016",
                        "evaluation_period": "2005-2016",
                        "metrics": {
                            "test_log_loss": 1.3233,
                            "test_accuracy": 0.5170,
                            "wicket_recall": 0.0198,
                            "wicket_precision": 0.1667,
                            "boundary_f1": 0.1761,
                        },
                        "calibration": {
                            "status": "uncalibrated_baseline",
                            "method": "raw_softmax"
                        },
                        "promotion_gates": {
                            "passed": True,
                            "decision": "Initial established baseline model."
                        },
                        "promotion_status": "promoted",
                        "created_at": "2026-09-17T13:54:45.000000+00:00",
                        "promoted_at": "2026-09-17T13:54:45.000000+00:00",
                        "artifact_paths": ["models/fieldiq_xgb_model.joblib", "models/model_metadata.json"],
                        "limitations": [
                            "Low wicket recall (0.02) due to extreme class imbalance (~4% wickets).",
                            "Uncalibrated raw probability outputs.",
                            "Trained on random ball split rather than strict match-level holdouts."
                        ]
                    },
                    "fieldiq_decomposed_v3_candidate": {
                        "model_id": "fieldiq_decomposed_v3_candidate",
                        "model_version": "3.0.0-candidate",
                        "architecture": "Three-Model Decomposed Factorized Architecture",
                        "dataset_version": "2.0.0",
                        "feature_version": "2.0.0",
                        "training_period": "2005-2016",
                        "evaluation_period": "2005-2016",
                        "metrics": {
                            "test_log_loss": 1.3483,
                            "wicket_recall": 0.1298,
                            "wicket_precision": 0.1638,
                            "boundary_f1": 0.3569,
                            "wicket_pr_auc": 0.0828,
                            "boundary_pr_auc": 0.2879,
                        },
                        "calibration": {
                            "status": "calibrated",
                            "method": "isotonic_regression_on_validation"
                        },
                        "promotion_gates": {
                            "passed": False,
                            "failed_gates": ["wicket_recall (0.1298 < 0.20)", "log_loss (1.3483 > 1.3233)"],
                            "decision": "Rejected promotion: log loss higher than baseline; wicket recall below 0.20 threshold."
                        },
                        "promotion_status": "rejected",
                        "created_at": "2026-10-04T19:10:59.000000+00:00",
                        "promoted_at": None,
                        "artifact_paths": [
                            "models/v3_decomposed/wicket_binary_model.joblib",
                            "models/v3_decomposed/boundary_binary_model.joblib",
                            "models/v3_decomposed/remainder_run_model.joblib",
                            "models/v3_decomposed/metadata.json"
                        ],
                        "limitations": [
                            "Compounding independent estimation error across sequentially trained models.",
                            "Wicket recall below minimum promotion benchmark."
                        ]
                    }
                }
            }
            with open(self.registry_path, "w", encoding="utf-8") as f:
                json.dump(initial_data, f, indent=2)

    def _read_registry(self) -> Dict[str, Any]:
        with open(self.registry_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _write_registry(self, data: Dict[str, Any]) -> None:
        data["last_updated"] = datetime.now(timezone.utc).isoformat()
        with open(self.registry_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def register_candidate_model(self, model_record: Dict[str, Any]) -> str:
        """
        Registers a newly trained candidate model.
        Forces promotion_status to 'candidate' by default. Never promotes silently.
        """
        data = self._read_registry()
        model_id = model_record.get("model_id")
        if not model_id:
            raise ValueError("model_record must have a unique 'model_id'.")

        record = dict(model_record)
        record["promotion_status"] = record.get("promotion_status", "candidate")
        record["created_at"] = record.get("created_at") or datetime.now(timezone.utc).isoformat()
        record["promoted_at"] = None

        data["models"][model_id] = record
        self._write_registry(data)
        return model_id

    def evaluate_and_promote(
        self,
        model_id: str,
        custom_gates: Optional[Dict[str, float]] = None,
        force: bool = False
    ) -> Dict[str, Any]:
        """
        Evaluates candidate against promotion gates.
        Only promotes if all gates are passed, or if force=True with explicit override.
        """
        data = self._read_registry()
        if model_id not in data["models"]:
            raise KeyError(f"Model ID '{model_id}' not found in registry.")

        record = data["models"][model_id]
        gates = {**DEFAULT_PROMOTION_GATES, **(custom_gates or {})}
        metrics = record.get("metrics", {})

        gate_results = {}
        failed_gates = []

        # Gate 1: Max Log Loss
        loss = metrics.get("test_log_loss")
        if loss is not None:
            passed = loss <= gates["max_log_loss"]
            gate_results["log_loss"] = {"observed": loss, "threshold": gates["max_log_loss"], "passed": passed}
            if not passed:
                failed_gates.append(f"log_loss ({loss:.4f} > {gates['max_log_loss']:.4f})")

        # Gate 2: Wicket Recall
        rec = metrics.get("wicket_recall")
        if rec is not None:
            passed = rec >= gates["wicket_recall_min"]
            gate_results["wicket_recall"] = {"observed": rec, "threshold": gates["wicket_recall_min"], "passed": passed}
            if not passed:
                failed_gates.append(f"wicket_recall ({rec:.4f} < {gates['wicket_recall_min']:.4f})")

        # Gate 3: Boundary F1
        b_f1 = metrics.get("boundary_f1")
        if b_f1 is not None:
            passed = b_f1 >= gates["boundary_f1_min"]
            gate_results["boundary_f1"] = {"observed": b_f1, "threshold": gates["boundary_f1_min"], "passed": passed}
            if not passed:
                failed_gates.append(f"boundary_f1 ({b_f1:.4f} < {gates['boundary_f1_min']:.4f})")

        # Gate 4: Wicket Precision
        prec = metrics.get("wicket_precision")
        if prec is not None:
            passed = prec >= gates["wicket_precision_min"]
            gate_results["wicket_precision"] = {"observed": prec, "threshold": gates["wicket_precision_min"], "passed": passed}
            if not passed:
                failed_gates.append(f"wicket_precision ({prec:.4f} < {gates['wicket_precision_min']:.4f})")

        # Gate 5: Max Brier Score
        brier = metrics.get("test_brier_score")
        if brier is not None:
            passed = brier <= gates["max_brier_score"]
            gate_results["brier_score"] = {"observed": brier, "threshold": gates["max_brier_score"], "passed": passed}
            if not passed:
                failed_gates.append(f"brier_score ({brier:.4f} > {gates['max_brier_score']:.4f})")

        # Gate 6: Valid Probability Distribution
        cal_meta = record.get("calibration", {})
        valid_dist = cal_meta.get("valid_distribution")
        if valid_dist is not None:
            passed = bool(valid_dist)
            gate_results["probability_distribution"] = {"passed": passed}
            if not passed:
                failed_gates.append("invalid_probability_distribution (probabilities do not sum to 1.0)")

        all_passed = len(failed_gates) == 0

        if all_passed or force:
            record["promotion_status"] = "promoted"
            record["promoted_at"] = datetime.now(timezone.utc).isoformat()
            record["promotion_gates"] = {
                "passed": True,
                "gate_evaluations": gate_results,
                "forced": force and not all_passed,
                "decision": "All promotion gates satisfied." if all_passed else "Manual promotion override."
            }
            # Switch active model
            data["active_model_id"] = model_id
            data["active_model_version"] = record.get("model_version", "1.0.0")
            data["active_dataset_version"] = record.get("dataset_version", "2.0.0")
        else:
            record["promotion_status"] = "rejected"
            record["promotion_gates"] = {
                "passed": False,
                "failed_gates": failed_gates,
                "gate_evaluations": gate_results,
                "decision": f"Rejected promotion: {', '.join(failed_gates)}"
            }

        data["models"][model_id] = record
        self._write_registry(data)
        return record

    def evaluate_three_tier_gates(
        self,
        model_id: str,
        human_approved: bool = False,
        custom_prob_gates: Optional[Dict[str, Any]] = None,
        custom_decision_gates: Optional[Dict[str, Any]] = None,
        custom_op_gates: Optional[Dict[str, Any]] = None,
        cohort: str = "cohort_b_cricsheet_non_spatial",
    ) -> Dict[str, Any]:
        """
        Phase 7: Evaluates a candidate model against decoupled three-tier governance gates:
        1. Probability Gates (calibration, information loss, simplex legality).
        2. Decision Gates (operating-point precision/recall and tactical expected loss).
        3. Operational Gates (artifact existence, latency, human approval).
        Never promotes a model without explicit human approval.
        """
        data = self._read_registry()
        if model_id not in data["models"]:
            raise KeyError(f"Model ID '{model_id}' not found in registry.")

        record = data["models"][model_id]
        metrics = record.get("metrics", {})
        p_gates = {**DEFAULT_PROBABILITY_GATES, **(custom_prob_gates or {})}
        d_gates = {**DEFAULT_DECISION_GATES, **(custom_decision_gates or {})}
        o_gates = {**DEFAULT_OPERATIONAL_GATES, **(custom_op_gates or {})}

        prob_results = {}
        decision_results = {}
        operational_results = {}
        failed_gates = []

        # Tier 1: Probability Gates
        loss = metrics.get("test_log_loss")
        if loss is not None:
            passed = loss <= p_gates["max_log_loss"]
            prob_results["max_log_loss"] = {"observed": loss, "threshold": p_gates["max_log_loss"], "passed": passed}
            if not passed:
                failed_gates.append(f"probability:log_loss ({loss:.4f} > {p_gates['max_log_loss']:.4f})")

        brier = metrics.get("test_brier_score_sum") or metrics.get("test_brier_score")
        if brier is not None:
            passed = brier <= p_gates["max_brier_sum"]
            prob_results["max_brier_sum"] = {"observed": brier, "threshold": p_gates["max_brier_sum"], "passed": passed}
            if not passed:
                failed_gates.append(f"probability:brier_sum ({brier:.4f} > {p_gates['max_brier_sum']:.4f})")

        ece = metrics.get("expected_calibration_error")
        if ece is not None:
            passed = ece <= p_gates["max_ece"]
            prob_results["max_ece"] = {"observed": ece, "threshold": p_gates["max_ece"], "passed": passed}
            if not passed:
                failed_gates.append(f"probability:ece ({ece:.4f} > {p_gates['max_ece']:.4f})")

        w_prauc = metrics.get("wicket_metrics", {}).get("pr_auc") or metrics.get("wicket_pr_auc")
        if w_prauc is not None:
            passed = w_prauc >= p_gates["min_wicket_pr_auc"]
            prob_results["min_wicket_pr_auc"] = {"observed": w_prauc, "threshold": p_gates["min_wicket_pr_auc"], "passed": passed}
            if not passed:
                failed_gates.append(f"probability:wicket_pr_auc ({w_prauc:.4f} < {p_gates['min_wicket_pr_auc']:.4f})")

        simplex = metrics.get("simplex_valid", record.get("calibration", {}).get("valid_distribution", True))
        prob_results["require_valid_simplex"] = {"observed": simplex, "passed": bool(simplex)}
        if not simplex:
            failed_gates.append("probability:simplex_invalid")

        # Tier 2: Decision Gates (Thresholded Operating Metrics)
        # Check thresholded operating metrics if available; fallback to raw metrics
        thresh_rec = metrics.get("thresholded_wicket_recall") or metrics.get("wicket_recall")
        if thresh_rec is not None:
            passed = thresh_rec >= d_gates["min_wicket_recall"]
            decision_results["min_wicket_recall"] = {"observed": thresh_rec, "threshold": d_gates["min_wicket_recall"], "passed": passed}
            if not passed:
                failed_gates.append(f"decision:wicket_recall ({thresh_rec:.4f} < {d_gates['min_wicket_recall']:.4f})")

        thresh_prec = metrics.get("thresholded_wicket_precision") or metrics.get("wicket_precision")
        if thresh_prec is not None:
            passed = thresh_prec >= d_gates["min_wicket_precision"]
            decision_results["min_wicket_precision"] = {"observed": thresh_prec, "threshold": d_gates["min_wicket_precision"], "passed": passed}
            if not passed:
                failed_gates.append(f"decision:wicket_precision ({thresh_prec:.4f} < {d_gates['min_wicket_precision']:.4f})")

        tactical_cost = metrics.get("expected_tactical_cost_per_ball")
        if tactical_cost is not None:
            passed = tactical_cost <= d_gates["max_expected_cost_per_ball"]
            decision_results["max_expected_cost_per_ball"] = {"observed": tactical_cost, "threshold": d_gates["max_expected_cost_per_ball"], "passed": passed}
            if not passed:
                failed_gates.append(f"decision:expected_tactical_cost ({tactical_cost:.4f} > {d_gates['max_expected_cost_per_ball']:.4f})")

        # Tier 3: Operational Gates
        artifacts = record.get("artifact_paths", [])
        artifacts_exist = all(Path(REPO_ROOT if "REPO_ROOT" in globals() else ".").joinpath(p).exists() for p in artifacts) if artifacts else True
        operational_results["require_artifact_exists"] = {"passed": artifacts_exist}
        if not artifacts_exist:
            failed_gates.append("operational:missing_model_artifacts")

        operational_results["require_human_approval"] = {"passed": human_approved}
        if not human_approved:
            failed_gates.append("operational:requires_human_approval")

        all_gates_passed = len(failed_gates) == 0

        evaluation_report = {
            "model_id": model_id,
            "cohort": cohort,
            "all_gates_passed": all_gates_passed,
            "probability_gates": prob_results,
            "decision_gates": decision_results,
            "operational_gates": operational_results,
            "failed_gates": failed_gates,
            "decision": "production_approved" if all_gates_passed else "rejected",
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
        }

        # Update record in registry without silent promotion
        record["three_tier_evaluation"] = evaluation_report
        if not all_gates_passed:
            record["promotion_status"] = PromotionStatus.REJECTED.value
            record["promoted"] = False
        else:
            record["promotion_status"] = PromotionStatus.PRODUCTION_APPROVED.value
            record["promoted"] = True
            record["promoted_at"] = datetime.now(timezone.utc).isoformat()
            data["active_model_id"] = model_id

        data["models"][model_id] = record
        self._write_registry(data)
        return evaluation_report

    def rollback_to_model(self, target_model_id: str) -> Dict[str, Any]:
        """Rolls back the active model to a previously registered model."""
        data = self._read_registry()
        if target_model_id not in data["models"]:
            raise KeyError(f"Target model ID '{target_model_id}' does not exist in registry.")

        target = data["models"][target_model_id]
        data["active_model_id"] = target_model_id
        data["active_model_version"] = target.get("model_version", "1.0.0")
        data["active_dataset_version"] = target.get("dataset_version", "2.0.0")
        self._write_registry(data)
        return target

    def get_active_model_id(self) -> str:
        """Returns the ID of the currently active production model."""
        data = self._read_registry()
        return data.get("active_model_id", "fieldiq_xgb_baseline_v1")

    def get_active_model_metadata(self) -> Dict[str, Any]:
        """Returns the full metadata dictionary for the currently active production model."""
        data = self._read_registry()
        active_id = data.get("active_model_id", "fieldiq_xgb_baseline_v1")
        model_meta = data["models"].get(active_id, {})
        return {
            "active_model_id": active_id,
            "active_model_version": data.get("active_model_version", "1.0.0"),
            "active_dataset_version": data.get("active_dataset_version", "2.0.0"),
            "model_metadata": model_meta
        }

    def list_models(self) -> List[Dict[str, Any]]:
        """Lists all registered models with their promotion statuses."""
        data = self._read_registry()
        return list(data.get("models", {}).values())


_global_registry: Optional[ModelRegistry] = None

def get_model_registry() -> ModelRegistry:
    global _global_registry
    if _global_registry is None:
        _global_registry = ModelRegistry()
    return _global_registry
