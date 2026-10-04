"""
test_bowler_type_vocabulary_contract.py
---------------------------------------
Contract tests ensuring bowler type enums, strings, and curated dictionary values
consistently normalize across the architecture without silent mismatch traps.

Prevents the class of bugs where enum names (e.g. 'RIGHT_ARM_FAST') fail to match
downstream string categories ('Pace' / 'Spin'), silently dropping to 'insufficient_data'.
"""
import pytest
import pandas as pd

from backend.app.services.profiles import BowlerType
from backend.app.services.bowler_style import (
    BOWLER_STYLE,
    BOWLER_TYPE_MAP,
    bowler_style,
    normalize_bowler_type,
)
from backend.app.services.h2h_stats_engine import H2HStatsEngine, get_h2h_stats_engine


def test_every_bowler_type_enum_maps_to_pace_or_spin():
    """Every member of BowlerType must explicitly map to 'Pace' or 'Spin'."""
    for b_type in BowlerType:
        norm_from_enum = normalize_bowler_type(b_type)
        norm_from_name = normalize_bowler_type(b_type.name)

        assert norm_from_enum in ("Pace", "Spin"), (
            f"BowlerType.{b_type.name} failed to map to 'Pace' or 'Spin'. Got: {norm_from_enum}"
        )
        assert norm_from_name in ("Pace", "Spin"), (
            f"String name '{b_type.name}' failed to map to 'Pace' or 'Spin'. Got: {norm_from_name}"
        )
        assert norm_from_enum == norm_from_name


def test_bowler_style_curated_entries_all_valid():
    """All curated bowler names in BOWLER_STYLE must map to valid categories."""
    assert len(BOWLER_STYLE) > 100, "Expected at least 100 curated bowlers in BOWLER_STYLE"
    valid_categories = {"Pace", "Spin", "Unknown"}

    for bowler_name, style in BOWLER_STYLE.items():
        assert style in valid_categories, f"Invalid style '{style}' for bowler '{bowler_name}'"
        assert bowler_style(bowler_name) == style
        assert normalize_bowler_type(bowler_name) == style


def test_bowler_type_map_aliases_and_case_insensitivity():
    """Tests case-insensitivity and standard aliases (e.g., 'pace', 'spin', 'FAST')."""
    assert normalize_bowler_type("pace") == "Pace"
    assert normalize_bowler_type("PACE") == "Pace"
    assert normalize_bowler_type("spin") == "Spin"
    assert normalize_bowler_type("SPIN") == "Spin"
    assert normalize_bowler_type("fast") == "Pace"
    assert normalize_bowler_type("right_arm_fast") == "Pace"
    assert normalize_bowler_type("off_spin") == "Spin"
    assert normalize_bowler_type("completely_invalid_type_xyz") == "Unknown"
    assert normalize_bowler_type(None) == "Unknown"


def test_h2h_engine_recognizes_every_bowler_type_enum():
    """
    Ensures H2HStatsEngine recognizes every BowlerType enum and produces
    Tier 2 or Tier 3 fallback instead of silently falling to 'insufficient_data'.
    Virat Kohli has 509 balls vs Pace and 357 balls vs Spin in the bundled dataset.
    """
    engine = get_h2h_stats_engine()

    for b_type in BowlerType:
        # Generic unknown bowler with explicit bowler_type enum
        stats = engine.get_matchup_stats(
            batter="Virat Kohli",
            bowler="Generic Test Bowler",
            bowler_type=b_type,
            phase="POWERPLAY",
        )

        # Must recognize the bowling style and hit Tier 2 (phase) or Tier 3 (overall)
        assert stats["source"] in ("vs_bowler_type_phase", "vs_bowler_type"), (
            f"H2HStatsEngine failed to recognize BowlerType.{b_type.name} for Virat Kohli: {stats}"
        )
        assert stats["balls_faced"] >= 30, (
            f"Expected >= 30 balls faced for Virat Kohli vs {b_type.name}, got {stats['balls_faced']}"
        )
        assert stats["strike_rate"] is not None
        assert stats["dismissal_rate"] is not None
