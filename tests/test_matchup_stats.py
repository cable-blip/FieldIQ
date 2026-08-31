from backend.app.services.matchup_stats import get_matchup_stats, initialize_matchup_stats

def test_initialize_and_get_matchup_stats_success() -> None:
    # Initialize matchup cache
    initialize_matchup_stats()
    
    # Test matchup with real history in the JSON dataset
    # NC Dodd vs A Khaka in real_match_dataset.json
    stats_dodd = get_matchup_stats("NC Dodd", "A Khaka")
    assert stats_dodd["has_history"] is True
    assert stats_dodd["balls_faced"] >= 1

    # SW Bates vs M Kapp
    stats_bates = get_matchup_stats("SW Bates", "M Kapp")
    assert stats_bates["has_history"] is True
    assert stats_bates["balls_faced"] >= 1

def test_matchup_stats_no_history() -> None:
    # Non-existent matchup has no history
    stats_none = get_matchup_stats("NonExistentBatter999", "NonExistentBowler999")
    assert stats_none["has_history"] is False
    assert stats_none["balls_faced"] == 0
    assert stats_none["runs_scored"] == 0
    assert stats_none["dismissals"] == 0
    assert stats_none["strike_rate"] == 0.0
