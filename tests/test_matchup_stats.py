from backend.app.services.matchup_stats import get_matchup_stats, initialize_matchup_stats

def test_initialize_and_get_matchup_stats_success() -> None:
    # Initialize matchup cache
    initialize_matchup_stats()
    
    # Test matchup with real history in the JSON dataset
    # HM Amla vs JR Hazlewood (Providence Stadium match 3)
    # HM Amla faces JR Hazlewood in over 0 (6 balls, 0 runs) and over 2 (1 ball, 1 run)
    stats_amla = get_matchup_stats("HM Amla", "JR Hazlewood")
    assert stats_amla["has_history"] is True
    assert stats_amla["balls_faced"] >= 7
    assert stats_amla["runs_scored"] >= 1
    assert stats_amla["dismissals"] == 0
    assert stats_amla["strike_rate"] > 0
    assert stats_amla["dot_ball_pct"] > 50

    # Q de Kock vs NM Coulter-Nile (over 1)
    # Q de Kock faces NM Coulter-Nile: 6 balls, 6 runs
    stats_kock = get_matchup_stats("Q de Kock", "NM Coulter-Nile")
    assert stats_kock["has_history"] is True
    assert stats_kock["balls_faced"] >= 6
    assert stats_kock["runs_scored"] >= 6
    assert stats_kock["strike_rate"] >= 100.0

def test_matchup_stats_no_history() -> None:
    # Virat Kohli has no bowler-level matchup entries in the JSON dataset
    stats_kohli = get_matchup_stats("Virat Kohli", "Mitchell Starc")
    assert stats_kohli["has_history"] is False
    assert stats_kohli["balls_faced"] == 0
    assert stats_kohli["runs_scored"] == 0
    assert stats_kohli["dismissals"] == 0
    assert stats_kohli["strike_rate"] == 0.0
