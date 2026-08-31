from backend.app.services.matchup_stats import get_matchup_stats, initialize_matchup_stats

def test_initialize_and_get_matchup_stats_success() -> None:
    # Initialize matchup cache
    initialize_matchup_stats()
    
    # Test matchup with real history in the JSON dataset
    # HM Amla vs JR Hazlewood
    stats_amla = get_matchup_stats("HM Amla", "JR Hazlewood")
    assert stats_amla["has_history"] is True
    assert stats_amla["balls_faced"] >= 7
    assert stats_amla["runs_scored"] >= 1
    assert stats_amla["strike_rate"] > 0

    # Q de Kock vs NM Coulter-Nile
    stats_kock = get_matchup_stats("Q de Kock", "NM Coulter-Nile")
    assert stats_kock["has_history"] is True
    assert stats_kock["balls_faced"] >= 6
    assert stats_kock["runs_scored"] >= 6
    assert stats_kock["strike_rate"] >= 100.0

def test_matchup_stats_no_history() -> None:
    # Non-existent matchup has no history
    stats_none = get_matchup_stats("NonExistentBatter999", "NonExistentBowler999")
    assert stats_none["has_history"] is False
    assert stats_none["balls_faced"] == 0
    assert stats_none["runs_scored"] == 0
    assert stats_none["dismissals"] == 0
    assert stats_none["strike_rate"] == 0.0
