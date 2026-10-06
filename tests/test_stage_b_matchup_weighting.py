"""
test_stage_b_matchup_weighting.py
-----------------------------------
Step 3 Verification Tests:
1. Tests that Stage B (run-saving zone optimization) is conditioned on empirical
   batter wagon wheels against specific bowler disciplines and direct matchups.
2. Tests that Left-Arm Fast (Starc) produces distinctly different ring and boundary
   fielder placements compared to Right-Arm Fast (Asif) for the same batter (Kohli).
3. Tests that direct H2H matchups (>=15 balls faced) resolve with 'direct_h2h' zone weighting.
4. Tests that unreviewed/associate bowlers resolve with 'insufficient_data' and fall back safely
   to baseline zone charts without errors or fabricated statistics.
5. Tests that all recommended fields satisfy ICC field legality constraints.
"""
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.profiles import resolve_batter_profile, resolve_bowler_profile, MatchPhase
from backend.app.services.h2h_stats_engine import get_h2h_stats_engine
from backend.app.services.optimizer import quick_recommend, recommend_field, get_sample_fielders, MatchFormat

client = TestClient(app)


def test_stage_b_differentiates_left_arm_vs_right_arm_pace():
    """
    Verifies that Stage B zone weighting genuinely differentiates between
    Left-Arm Fast (Starc) and Right-Arm Fast (Asif) for Virat Kohli:
    - Stage A cordon differs (Gully elevated over 2nd Slip for Starc).
    - Stage B ring and boundary placements differ based on empirical wagon-wheel scoring.
    """
    res_asif = quick_recommend("Virat Kohli", "Mohammad Asif", 3, "T20")
    res_starc = quick_recommend("Virat Kohli", "Mitchell Starc", 3, "T20")

    # Both must be complete and legal
    assert res_asif.is_legal is True
    assert res_starc.is_legal is True
    assert len(res_asif.placements) == 11
    assert len(res_starc.placements) == 11

    asif_positions = [p.position_name for p in res_asif.placements]
    starc_positions = [p.position_name for p in res_starc.placements]

    # The field placements as a whole MUST differ
    assert asif_positions != starc_positions

    # Extract Stage B positions (non-wicketkeeping, non-bowler, non-cordon)
    cordon = {"1st Slip", "2nd Slip", "Gully", "Wicketkeeper", "Bowler"}
    asif_stage_b = [p for p in asif_positions if p not in cordon]
    starc_stage_b = [p for p in starc_positions if p not in cordon]

    # Stage B positions MUST NOT be identical (resolves Finding 7 sub-finding)
    assert asif_stage_b != starc_stage_b

    # Against Asif (RAF), Kohli drives straight -> Long On is placed
    assert "Long On" in asif_positions
    # Against Starc (LAF), the angled delivery drives balls squarer/behind point
    assert ("Deep Point" in starc_positions) or ("Third Man" in starc_positions)


def test_stage_b_direct_h2h_matchup_weighting():
    """
    Verifies that direct H2H matchups (>=15 balls faced in real dataset)
    resolve with 'direct_h2h' zone weighting.
    E.g. Kumar Sangakkara vs Daniel Vettori (50 balls faced) or Virat Kohli vs Imran Tahir (19 balls).
    """
    h2h_engine = get_h2h_stats_engine()
    chart, source = h2h_engine.get_matchup_zone_chart(
        batter="Virat Kohli",
        bowler="Imran Tahir",
        bowler_type="LEG_SPIN",
        phase="MIDDLE"
    )

    assert source == "direct_h2h"
    assert chart is not None
    assert len(chart) == 24  # 8 directions x 3 bands

    # Verify that optimizer includes the direct_h2h explanation
    res = quick_recommend("Virat Kohli", "Imran Tahir", 8, "T20")
    assert any("[direct_h2h]" in exp for exp in res.tactical_explanations)


def test_stage_b_unreviewed_bowler_safe_fallback():
    """
    Verifies that an unreviewed bowler with no style classification (Ahsan Malik)
    resolves with 'insufficient_data' and safely falls back to baseline batter.zone_chart.
    """
    h2h_engine = get_h2h_stats_engine()
    chart, source = h2h_engine.get_matchup_zone_chart(
        batter="Virat Kohli",
        bowler="Ahsan Malik",
        bowler_type="Unknown",
        phase="POWERPLAY"
    )

    assert source == "insufficient_data"
    assert chart is None

    # Optimizer must still run safely, producing a legal field
    res = quick_recommend("Virat Kohli", "Ahsan Malik", 3, "T20")
    assert res.is_legal is True
    assert len(res.violations) == 0
    assert len(res.placements) == 11


def test_api_analysis_endpoint_reflects_matchup_weighted_stage_b():
    """
    Verifies that POST /api/v1/analysis runs successfully and returns legal placements
    with matchup-conditioned explanations.
    """
    response = client.post(
        "/api/v1/analysis",
        json={
            "batter_name": "Virat Kohli",
            "bowler_name": "Mitchell Starc",
            "match_format": "T20",
            "innings": 1,
            "over": 3,
            "runs": 22,
            "wickets": 0,
            "tactical_objective": "attack_wicket"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_legal"] is True
    assert len(data["placements"]) == 11
    positions = [p["position_name"] for p in data["placements"]]
    assert "Gully" in positions
    assert ("Deep Point" in positions) or ("Third Man" in positions)
