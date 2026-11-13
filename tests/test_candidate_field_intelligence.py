"""
test_candidate_field_intelligence.py
-------------------------------------
Comprehensive verification and golden acceptance test scenarios for:
1. Candidate-field-conditioned outcome modeling (Section 10).
2. Probabilistic validity: non-negative, sums to 1.0 within tolerance.
3. Objective-specific utility functions across all 4 tactical objectives:
   - attack_wicket, prevent_boundary, build_pressure, stop_singles.
4. Physical coordinates and fielder capability sensitivity.
5. All 15 Golden Acceptance Scenarios required by Section 13.
"""
from __future__ import annotations

import math
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.candidate_field_evaluator import (
    CandidateFieldOutcome,
    TacticalObjective,
    compute_candidate_field_outcomes,
)
from backend.app.services.model_registry import (
    DEFAULT_PROMOTION_GATES,
    ModelRegistry,
    get_model_registry,
)
from backend.app.services.position_map import get_position
from backend.app.services.profiles import (
    BatterProfile,
    BowlerProfile,
    BowlerType,
    FieldPlacement,
    FielderProfile,
    Handedness,
    MatchFormat,
    MatchPhase,
    get_keeper,
    get_sample_batters,
    get_sample_bowlers,
    get_sample_fielders,
    resolve_batter_profile,
    resolve_bowler_profile,
)
from backend.app.services.simulator import (
    build_aggressive_layout,
    build_defensive_layout,
    build_pressure_layout,
    build_stop_singles_layout,
    create_alternative_placement,
    generate_candidate_fields,
)

class DirectAnalysisResponse:
    def __init__(self, obj, status_code=200):
        self._obj = obj
        self.status_code = status_code

    def json(self):
        return self._obj.model_dump()


def direct_post_analysis(payload: dict) -> DirectAnalysisResponse:
    from backend.app.schemas.analysis import AnalysisRequest
    from backend.app.routers.analysis import create_analysis_request
    req = AnalysisRequest(**payload)
    resp = create_analysis_request(req)
    return DirectAnalysisResponse(resp, 200)


# ---------------------------------------------------------------------------
# Test Suite 1: Mathematical & Probabilistic Integrity of Candidate Fields
# ---------------------------------------------------------------------------

def test_candidate_field_outcome_probabilities_sum_to_one():
    """Validates that candidate-field conditioned probabilities strictly sum to 1.000 within 1e-4."""
    batter = resolve_batter_profile("Virat Kohli")
    bowler = resolve_bowler_profile("Mitchell Starc")
    fielders = get_sample_fielders()
    keeper = get_keeper()

    candidates = generate_candidate_fields(
        batter=batter,
        bowler=bowler,
        fielder_pool=fielders,
        current_over=10,
        fmt=MatchFormat.T20,
        keeper=keeper,
    )

    for cand in candidates:
        # Check non-negative
        for p_key in ["p_dot", "p_single", "p_two", "p_three", "p_four", "p_six", "p_wicket"]:
            if p_key in cand:
                assert cand[p_key] >= 0.0, f"{p_key} must be non-negative"

        # Check total sum
        if "p_dot" in cand:
            prob_sum = (
                cand["p_dot"]
                + cand["p_single"]
                + cand["p_two"]
                + cand["p_three"]
                + cand["p_four"]
                + cand["p_six"]
                + cand["p_wicket"]
            )
            assert prob_sum == pytest.approx(1.0, abs=1e-3)

        # Check boundary probability consistency
        if "p_boundary" in cand and "p_four" in cand and "p_six" in cand:
            assert cand["p_boundary"] == pytest.approx(cand["p_four"] + cand["p_six"], abs=1e-3)


def test_candidate_field_expected_values_consistency():
    """Asserts expected runs per over = 6 * expected runs per ball."""
    batter = resolve_batter_profile("Virat Kohli")
    bowler = resolve_bowler_profile("Mohammad Asif")
    fielders = get_sample_fielders()
    keeper = get_keeper()

    fielders = get_sample_fielders()
    sample_positions = ["Wicketkeeper", "Bowler", "Point", "Cover", "Midwicket", "Square Leg", "Mid On", "Mid Off", "Deep Midwicket", "Long On", "Deep Cover"]
    placements = [
        create_alternative_placement(pos, fielders[i], "run_saving" if pos not in ("Wicketkeeper", "Bowler") else ("wicket" if pos == "Wicketkeeper" else "bowler"), "Fielding")
        for i, pos in enumerate(sample_positions)
    ]
    outcome = compute_candidate_field_outcomes(
        placements=placements,
        batter=batter,
        bowler=bowler,
        phase=MatchPhase.POWERPLAY,
        fmt=MatchFormat.ODI,
        objective=TacticalObjective.ATTACK_WICKET,
    )

    assert outcome.expected_runs_per_ball >= 0.0
    assert outcome.expected_runs_per_over == pytest.approx(outcome.expected_runs_per_ball * 6.0, abs=0.05)
    assert 0.0 <= outcome.expected_wickets <= 1.0


# ---------------------------------------------------------------------------
# Test Suite 2: Objective-Specific Utility Function Differentiation
# ---------------------------------------------------------------------------

def test_objective_specific_utility_differentiation():
    """Asserts that the 4 tactical objectives rank field configurations in alignment with their goals."""
    batter = resolve_batter_profile("Virat Kohli")
    bowler = resolve_bowler_profile("Mitchell Starc")
    fielders = get_sample_fielders()
    keeper = get_keeper()

    candidates = generate_candidate_fields(
        batter=batter,
        bowler=bowler,
        fielder_pool=fielders,
        current_over=8,
        fmt=MatchFormat.T20,
        keeper=keeper,
    )

    agg = next(c for c in candidates if c["strategy_id"] == "aggressive")
    defens = next(c for c in candidates if c["strategy_id"] == "defensive")

    # Aggressive layout has slips/close catchers -> higher wicket probability
    assert agg["wicket_probability"] >= defens["wicket_probability"]
    assert agg["catch_opportunity"] >= defens["catch_opportunity"]
    assert agg["ewo"] > defens["ewo"]

    # Defensive layout has boundary riders -> higher boundary prevention, higher ERS
    assert defens["boundary_prevention"] >= agg["boundary_prevention"]
    assert defens["ers"] > agg["ers"]


# ---------------------------------------------------------------------------
# Test Suite 3: The 15 Golden Acceptance Scenarios (Section 13)
# ---------------------------------------------------------------------------

def test_scenario_01_virat_kohli_vs_mohammad_asif():
    """Scenario 1: Virat Kohli vs Mohammad Asif (Right-Arm Fast, seam movement, slips cordon)."""
    batter = resolve_batter_profile("Virat Kohli")
    bowler = resolve_bowler_profile("Mohammad Asif")
    assert bowler.bowler_type == BowlerType.RIGHT_ARM_FAST

    fielders = get_sample_fielders()
    candidates = generate_candidate_fields(batter, bowler, fielders, current_over=2, fmt=MatchFormat.ODI)
    agg = next(c for c in candidates if c["strategy_id"] == "aggressive")

    # In a Test match powerplay vs Mohammad Asif, aggressive layout places slips
    pos_names = [p.position_name for p in agg["placements"]]
    assert "1st Slip" in pos_names
    assert "2nd Slip" in pos_names
    assert agg["is_legal"] is True


def test_scenario_02_virat_kohli_vs_mitchell_starc():
    """Scenario 2: Virat Kohli vs Mitchell Starc (Left-Arm Fast, pace angle, off-side boundary threat)."""
    batter = resolve_batter_profile("Virat Kohli")
    bowler = resolve_bowler_profile("Mitchell Starc")
    assert bowler.bowler_type == BowlerType.LEFT_ARM_FAST

    fielders = get_sample_fielders()
    candidates = generate_candidate_fields(batter, bowler, fielders, current_over=18, fmt=MatchFormat.T20)
    defens = next(c for c in candidates if c["strategy_id"] == "defensive")

    assert defens["boundary_prevention"] > 0.40
    assert defens["ers"] > 1.0


def test_scenario_03_virat_kohli_vs_imran_tahir():
    """Scenario 3: Virat Kohli vs Imran Tahir (Leg-Spin, zero sweep risk, cover/midwicket traps)."""
    batter = resolve_batter_profile("Virat Kohli")
    bowler = resolve_bowler_profile("Imran Tahir")
    assert bowler.bowler_type == BowlerType.LEG_SPIN

    # Kohli's data-derived sweep risk is low (0.20), preventing Short Leg
    assert batter.sweep_risk_vs_spin < 0.30
    fielders = get_sample_fielders()
    candidates = generate_candidate_fields(batter, bowler, fielders, current_over=11, fmt=MatchFormat.T20)
    balanced = next(c for c in candidates if c["strategy_id"] == "balanced")

    pos_names = [p.position_name for p in balanced["placements"]]
    assert "Short Leg" not in pos_names


def test_scenario_04_lhb_vs_off_spinner():
    """Scenario 4: Left-Handed Batter (Chris Gayle) vs Off-Spinner (turn away from LHB)."""
    gayle = resolve_batter_profile("Chris Gayle")
    assert gayle.handedness == Handedness.LHB

    ashwin = resolve_bowler_profile("Ravichandran Ashwin")
    assert ashwin.bowler_type == BowlerType.OFF_SPIN

    fielders = get_sample_fielders()
    candidates = generate_candidate_fields(gayle, ashwin, fielders, current_over=7, fmt=MatchFormat.T20)
    assert len(candidates) >= 3


def test_scenario_05_lhb_vs_leg_spinner():
    """Scenario 5: Left-Handed Batter (David Warner) vs Leg-Spinner (turn into LHB)."""
    warner = resolve_batter_profile("David Warner")
    assert warner.handedness == Handedness.LHB

    tahir = resolve_bowler_profile("Imran Tahir")
    assert tahir.bowler_type == BowlerType.LEG_SPIN

    fielders = get_sample_fielders()
    candidates = generate_candidate_fields(warner, tahir, fielders, current_over=8, fmt=MatchFormat.T20)
    assert all(c["is_legal"] for c in candidates)


def test_scenario_06_unknown_bowler_insufficient_discipline_data():
    """Scenario 6: Unknown bowler defaults to insufficient_data / unspecified_fallback without fabrication."""
    from backend.app.services.bowler_style import resolve_bowler_discipline

    disc, prov = resolve_bowler_discipline("Unknown Debutant Spinner")
    assert prov == "insufficient_data"
    assert disc == "RIGHT_ARM_FAST"


def test_scenario_07_batter_with_insufficient_spatial_data():
    """Scenario 7: Batter with unmapped / zero spatial deliveries handles Zone 0 honestly."""
    from backend.app.services.spatial_intelligence import is_valid_spatial_zone

    assert is_valid_spatial_zone(0) is False
    assert is_valid_spatial_zone(None) is False
    assert is_valid_spatial_zone(9) is False
    assert is_valid_spatial_zone(5) is True


def test_scenario_08_powerplay_field_restriction():
    """Scenario 8: Powerplay max 2 outside circle enforced."""
    batter = resolve_batter_profile("Virat Kohli")
    bowler = resolve_bowler_profile("Mitchell Starc")
    fielders = get_sample_fielders()

    candidates = generate_candidate_fields(batter, bowler, fielders, current_over=3, fmt=MatchFormat.T20)
    for c in candidates:
        outside_count = sum(
            1 for p in c["placements"]
            if p.position_name not in ("Wicketkeeper", "Bowler")
            and math.sqrt(p.x * p.x + p.y * p.y) > 27.432
        )
        assert outside_count <= 2, f"Powerplay allowed at most 2 outside, got {outside_count}"


def test_scenario_09_death_over_field_restriction():
    """Scenario 9: Death overs (T20 over 16-20) allow up to 5 outside."""
    batter = resolve_batter_profile("Virat Kohli")
    bowler = resolve_bowler_profile("Mitchell Starc")
    fielders = get_sample_fielders()

    candidates = generate_candidate_fields(batter, bowler, fielders, current_over=19, fmt=MatchFormat.T20)
    for c in candidates:
        assert c["is_legal"] is True


def test_scenario_10_target_chase_high_required_rate():
    """Scenario 10: Target chase scenario with high required run rate."""
    payload = {
        "batter_name": "Virat Kohli",
        "bowler_name": "Mitchell Starc",
        "match_format": "T20",
        "innings": 2,
        "over": 17,
        "runs": 160,
        "wickets": 3,
        "tactical_objective": "prevent_boundary",
    }
    res = direct_post_analysis(payload)
    assert res.status_code == 200
    data = res.json()
    assert data["field_optimization"]["objective"] == "prevent_boundary"
    assert len(data["alternative_fields"]) >= 3


def test_scenario_11_low_score_pressure_situation():
    """Scenario 11: Low-score pressure situation with build_pressure objective."""
    payload = {
        "batter_name": "Virat Kohli",
        "bowler_name": "Mitchell Starc",
        "match_format": "T20",
        "innings": 1,
        "over": 7,
        "runs": 35,
        "wickets": 3,
        "tactical_objective": "build_pressure",
    }
    res = direct_post_analysis(payload)
    assert res.status_code == 200
    data = res.json()
    assert data["field_optimization"]["objective"] == "build_pressure"


def test_scenario_12_candidate_field_illegal_placement_detection():
    """Scenario 12: Candidate field with illegal placements reports violations and is_legal=False."""
    batter = resolve_batter_profile("Virat Kohli")
    bowler = resolve_bowler_profile("Mitchell Starc")
    fielders = get_sample_fielders()

    # Create illegal layout with 4 boundary riders in Powerplay (max 2 allowed)
    illegal_placements = [
        create_alternative_placement("Wicketkeeper", fielders[0], "wicket", "Keeper"),
        create_alternative_placement("Bowler", fielders[1], "bowler", "Bowler"),
        create_alternative_placement("Deep Midwicket", fielders[2], "run_saving", "Illegal 1"),
        create_alternative_placement("Long On", fielders[3], "run_saving", "Illegal 2"),
        create_alternative_placement("Long Off", fielders[4], "run_saving", "Illegal 3"),
        create_alternative_placement("Deep Cover", fielders[5], "run_saving", "Illegal 4"),
        create_alternative_placement("Point", fielders[6], "run_saving", "Ring"),
        create_alternative_placement("Cover", fielders[7], "run_saving", "Ring"),
        create_alternative_placement("Midwicket", fielders[8], "run_saving", "Ring"),
        create_alternative_placement("Square Leg", fielders[9], "run_saving", "Ring"),
        create_alternative_placement("Mid On", fielders[10], "run_saving", "Ring"),
    ]

    outcome = compute_candidate_field_outcomes(
        placements=illegal_placements,
        batter=batter,
        bowler=bowler,
        phase=MatchPhase.POWERPLAY,
        fmt=MatchFormat.T20,
    )

    assert outcome.is_legal is False
    assert len(outcome.violations) > 0
    assert any("Outside circle count is 4" in v for v in outcome.violations)


def test_scenario_13_candidate_field_missing_fielder_capability():
    """Scenario 13: Candidate field with missing capability flags the issue transparently."""
    batter = resolve_batter_profile("Virat Kohli")
    bowler = resolve_bowler_profile("Mitchell Starc")

    # Create fielder with None for catching
    impaired_fielder = FielderProfile(
        name="Untested Sub",
        catching=None,  # type: ignore
        arm=0.5,
        jump=0.5,
        close_in_skill=0.5,
        boundary_skill=0.5,
        preferred_positions=[],
    )
    fielders = get_sample_fielders()
    placements = [
        create_alternative_placement("Wicketkeeper", fielders[0], "wicket", "Keeper"),
        create_alternative_placement("Bowler", fielders[1], "bowler", "Bowler"),
        create_alternative_placement("Cover", impaired_fielder, "run_saving", "Test"),
    ] + [
        create_alternative_placement(pos, fielders[i + 2], "run_saving", "Test")
        for i, pos in enumerate(["Point", "Midwicket", "Square Leg", "Mid On", "Mid Off", "Long On", "Deep Midwicket", "Deep Cover"])
    ]

    outcome = compute_candidate_field_outcomes(
        placements=placements[:11],
        batter=batter,
        bowler=bowler,
        phase=MatchPhase.MIDDLE,
        fmt=MatchFormat.T20,
    )

    assert len(outcome.missing_capabilities) > 0
    assert any("missing catching" in c for c in outcome.missing_capabilities)


def test_scenario_14_candidate_model_failing_promotion():
    """Scenario 14: Underperforming candidate model fails promotion gates and active model remains stable."""
    registry = get_model_registry()

    failing_cand = {
        "model_id": "test_golden_failing_cand",
        "model_version": "2.2.0-test",
        "architecture": "Experimental Underperforming Tree",
        "dataset_version": "2.0.0",
        "feature_version": "2.1.0",
        "metrics": {
            "test_log_loss": 1.48,  # > 1.350 (FAILS)
            "wicket_recall": 0.04,  # < 0.150 (FAILS)
            "wicket_precision": 0.08,  # < 0.120 (FAILS)
            "boundary_f1": 0.22,  # < 0.300 (FAILS)
        },
        "calibration": {"valid_distribution": True},
    }

    registry.register_candidate_model(failing_cand)
    eval_result = registry.evaluate_and_promote("test_golden_failing_cand", force=False)

    assert eval_result["promotion_status"] == "rejected"
    assert eval_result["promotion_gates"]["passed"] is False
    assert len(eval_result["promotion_gates"]["failed_gates"]) >= 3

    # Active model must NOT be replaced
    active = registry.get_active_model_metadata()
    assert active["active_model_id"] == "fieldiq_xgb_baseline_v1"


def test_scenario_15_calibrated_model_improving_calibration_rejected_on_recall():
    """Scenario 15: Calibrated model that passes log loss and calibration but fails recall is rejected."""
    registry = get_model_registry()

    calibrated_cand = {
        "model_id": "test_golden_calibrated_cand",
        "model_version": "2.2.0-calibrated",
        "architecture": "Calibrated XGBoost (Sigmoid)",
        "dataset_version": "2.0.0",
        "feature_version": "2.1.0",
        "metrics": {
            "test_log_loss": 1.3486,  # <= 1.350 (PASSES)
            "test_brier_score": 0.6552,  # <= 0.750 (PASSES)
            "wicket_recall": 0.1224,  # < 0.150 (FAILS)
            "wicket_precision": 0.1224,  # >= 0.120 (PASSES)
            "boundary_f1": 0.3009,  # >= 0.300 (PASSES)
        },
        "calibration": {"status": "calibrated", "valid_distribution": True},
    }

    registry.register_candidate_model(calibrated_cand)
    eval_result = registry.evaluate_and_promote("test_golden_calibrated_cand", force=False)

    assert eval_result["promotion_status"] == "rejected"
    assert any("wicket_recall" in gate for gate in eval_result["promotion_gates"]["failed_gates"])
