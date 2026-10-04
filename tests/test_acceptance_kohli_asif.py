"""
test_acceptance_kohli_asif.py
-----------------------------
Phase 4: Acceptance test proving the single end-to-end tactical walking skeleton.

Master Plan Scenario (Step 4.1):
"Virat Kohli is batting against Mohammad Asif, T20, over 3, score 28/0.
The system returns a legal 11-player field.
The field places a fielder at a position justified by Kohli's real h2h/zone data against Asif.
The response tells me the wicket probability and whether that number is backed by direct h2h data or a fallback tier."
"""
from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_full_pipeline_kohli_vs_asif():
    """
    Executes the exact Phase 4 end-to-end acceptance scenario.
    Asserts specific numbers, legal constraints, and honest tiered data provenance.
    """
    response = client.post(
        "/api/v1/analysis",
        json={
            "batter_name": "Virat Kohli",
            "bowler_name": "Mohammad Asif",
            "match_format": "T20",
            "innings": 1,
            "over": 3,
            "runs": 28,
            "wickets": 0,
            "tactical_objective": "attack_wicket",
        },
    )

    # 1. Synchronous REST Contract
    assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}: {response.text}"
    data = response.json()
    assert data["status"] == "available"

    # 2. Legality & 11-Player Placements
    assert len(data["placements"]) == 11, f"Expected exactly 11 placements, got {len(data['placements'])}"
    assert data["is_legal"] is True, f"Generated illegal field: {data.get('violations')}"
    assert len(data.get("violations", [])) == 0

    # Ensure Bowler and Wicketkeeper are present
    roles = [p["role"] for p in data["placements"]]
    pos_names = [p["position_name"].lower() for p in data["placements"]]
    assert any("wicketkeeper" in p for p in pos_names), "Missing Wicketkeeper"
    assert any("bowler" in p for p in pos_names), "Missing Bowler"

    # Powerplay fielding circle constraint: maximum 2 fielders outside 30-yard circle
    # In FieldIQ coordinate system, 30-yard circle is ~27.4m radius.
    # We verify that placements respect the Powerplay legal limit.
    outside_circle = [p for p in data["placements"] if (p["x"]**2 + p["y"]**2)**0.5 > 27.4]
    assert len(outside_circle) <= 2, f"Powerplay violation: {len(outside_circle)} fielders outside 30y circle"

    # 3. Honest Tiered Data Coverage Provenance
    # Asif has 0 direct deliveries vs Kohli in the dataset.
    # Therefore, the system MUST NOT claim direct_h2h; it must activate Tier 2
    # ('vs_bowler_type_phase') for Kohli vs Pace in Powerplay (232 balls).
    assert data["data_coverage"] == "vs_bowler_type_phase", (
        f"Expected data_coverage='vs_bowler_type_phase', got '{data.get('data_coverage')}'"
    )

    m_stats = data["matchup_stats"]
    assert m_stats["source"] == "vs_bowler_type_phase"
    assert m_stats["balls_faced"] == 232, f"Expected 232 balls faced vs Pace in Powerplay, got {m_stats['balls_faced']}"
    assert m_stats["dismissals"] == 4, f"Expected 4 dismissals vs Pace in Powerplay, got {m_stats['dismissals']}"
    assert m_stats["strike_rate"] == 124.14
    assert m_stats["dot_ball_pct"] == 40.09
    assert m_stats["boundary_pct"] == 18.97
    assert "232 balls faced vs Pace in POWERPLAY phase" in m_stats["data_coverage_note"]

    # 4. Explicit Model Confidence and Outcome Probabilities Disclosed
    assert data["ml_probabilities"] is not None
    ml_probs = data["ml_probabilities"]
    assert "wicket_pct" in ml_probs
    assert ml_probs["wicket_pct"] > 0.0, "Expected non-zero wicket probability"
    assert ml_probs["expected_runs_per_ball"] > 0.0

    assert data["model_confidence"] is not None
    assert data["model_confidence"]["wicket_prediction_recall"] == 0.02
    assert data["model_confidence"]["wicket_prediction_precision"] == 0.167
    assert data["model_confidence"]["status"] == "uncalibrated_baseline"

    # 5. Bowler Provenance Disclosed
    assert data["bowler_provenance"] is not None
    assert data["bowler_provenance"]["bowler_type"] == "curated_categorical"

    # 6. Tactical Placements grounded in Kohli's profile
    # Kohli heavily favors Zone 3 (cover/point) and Zone 6 (midwicket)
    # Attack wicket objective must deploy close catching positions (slip / gully)
    slip_gully_positions = [
        p["position_name"] for p in data["placements"]
        if any(term in p["position_name"].lower() for term in ["slip", "gully", "point", "cover"])
    ]
    assert len(slip_gully_positions) >= 2, f"Expected attacking catching/ring placements for Kohli, got: {pos_names}"
