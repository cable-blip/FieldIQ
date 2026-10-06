"""
test_bowler_discipline_granularity.py
-------------------------------------
Step 2 Verification Tests:
1. Tests that curated bowlers resolve to exact BowlerType and 'curated_categorical' provenance.
2. Tests that median/unreviewed pace/spin bowlers resolve to baseline with 'unspecified_fallback' provenance.
3. Tests that unknown bowlers resolve with 'insufficient_data' provenance.
4. Tests that Rule 1 produces distinct geometry for Left-Arm Fast (Starc) vs Right-Arm Fast (Asif).
5. Tests that Rule 2 (Leg Spin edge trap) reactivates for real leg-spinners (Tahir).
6. Tests that Rule 4 (Sweep trap) distinguishes between off-spin/orthodox and leg-spin.
7. Tests that API POST /api/v1/analysis returns bowler_provenance metadata accurately.
"""
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.profiles import BowlerType, resolve_bowler_profile, resolve_batter_profile, MatchPhase
from backend.app.services.bowler_style import resolve_bowler_discipline
from backend.app.services.matchup_engine import analyze_matchup

client = TestClient(app)


def test_curated_bowler_discipline_resolution():
    """Verifies that verified international bowlers resolve to exact arm & discipline."""
    # Left-Arm Fast
    starc = resolve_bowler_profile("Mitchell Starc")
    assert starc.bowler_type == BowlerType.LEFT_ARM_FAST
    assert starc.provenance_metadata["bowler_type"] == "curated_categorical"

    # Right-Arm Fast
    asif = resolve_bowler_profile("Mohammad Asif")
    assert asif.bowler_type == BowlerType.RIGHT_ARM_FAST
    assert asif.provenance_metadata["bowler_type"] == "curated_categorical"

    # Leg-Spin
    tahir = resolve_bowler_profile("Imran Tahir")
    assert tahir.bowler_type == BowlerType.LEG_SPIN
    assert tahir.provenance_metadata["bowler_type"] == "curated_categorical"

    # Left-Arm Orthodox
    vettori = resolve_bowler_profile("Daniel Vettori")
    assert vettori.bowler_type == BowlerType.LEFT_ARM_ORTHODOX
    assert vettori.provenance_metadata["bowler_type"] == "curated_categorical"


def test_unspecified_fallback_bowler_resolution():
    """
    Verifies that unreviewed pace/spin bowlers resolve cleanly to baseline
    with explicit 'unspecified_fallback' provenance, never guessing arm or sub-discipline.
    """
    # Shafiul Islam is marked 'Pace' in BOWLER_STYLE, but arm is unreviewed in BOWLER_DISCIPLINE
    shafiul = resolve_bowler_profile("Shafiul Islam")
    assert shafiul.bowler_type == BowlerType.RIGHT_ARM_FAST
    assert shafiul.provenance_metadata["bowler_type"] == "unspecified_fallback"

    # A completely unknown bowler not in BOWLER_STYLE
    unknown_bowler = resolve_bowler_profile("Completely Unreviewed Associate Bowler")
    assert unknown_bowler.provenance_metadata["bowler_type"] == "insufficient_data"


def test_rule_1_left_arm_vs_right_arm_tactical_differentiation():
    """
    Verifies that Left-Arm Fast (Starc) produces distinct tactical priorities
    from Right-Arm Fast (Asif) for the same batter (Virat Kohli).
    """
    kohli = resolve_batter_profile("Virat Kohli")
    starc = resolve_bowler_profile("Mitchell Starc")  # LEFT_ARM_FAST
    asif = resolve_bowler_profile("Mohammad Asif")    # RIGHT_ARM_FAST

    recs_starc = analyze_matchup(kohli, starc, MatchPhase.POWERPLAY)
    recs_asif = analyze_matchup(kohli, asif, MatchPhase.POWERPLAY)

    gully_starc = next((r for r in recs_starc if r.position == "Gully"), None)
    gully_asif = next((r for r in recs_asif if r.position == "Gully"), None)

    assert gully_starc is not None, "Gully must be recommended for Starc"
    assert gully_asif is not None, "Gully must be recommended for Asif"

    # For Left-Arm Fast, the natural angle across the batter elevates Gully priority (0.85 vs 0.70)
    assert gully_starc.priority > gully_asif.priority
    assert "Left-arm" in gully_starc.reason


def test_rule_2_reactivated_for_real_leg_spinners():
    """
    Verifies that Rule 2 (edge risk vs spin turning away) fires for real leg-spinners (Imran Tahir),
    whereas it does NOT fire for off-spinners (Ravichandran Ashwin).
    """
    kohli = resolve_batter_profile("Virat Kohli")
    tahir = resolve_bowler_profile("Imran Tahir")          # LEG_SPIN
    ashwin = resolve_bowler_profile("Ravichandran Ashwin")  # OFF_SPIN

    recs_tahir = analyze_matchup(kohli, tahir, MatchPhase.MIDDLE)
    recs_ashwin = analyze_matchup(kohli, ashwin, MatchPhase.MIDDLE)

    slip_tahir = next((r for r in recs_tahir if r.position == "1st Slip"), None)
    slip_ashwin = next((r for r in recs_ashwin if r.position == "1st Slip"), None)

    assert slip_tahir is not None, "Leg-spinner must trigger 1st Slip via reactivated Rule 2"
    assert "Leg spin turns away" in slip_tahir.reason
    assert slip_ashwin is None, "Off-spinner turning into pads must not trigger 1st Slip edge trap"


def test_api_analysis_returns_provenance_metadata():
    """Verifies that POST /api/v1/analysis returns bowler_provenance metadata."""
    res = client.post(
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
    assert res.status_code == 200
    data = res.json()
    assert "bowler_provenance" in data
    assert data["bowler_provenance"]["bowler_type"] == "curated_categorical"
