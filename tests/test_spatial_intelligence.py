"""
test_spatial_intelligence.py
----------------------------
Comprehensive verification for the transparent, provenance-aware spatial intelligence layer:
1. Domain validity: is_valid_spatial_zone strictly accepts 1..8 and rejects 0, None, strings, out-of-bounds.
2. Distribution separation: Directional shot distribution P(zone | valid deliveries) vs Outcome distribution P(runs | zone).
3. Statistical shrinkage: Empirical Bayes shrinkage behavior for sparse vs abundant directional data.
4. Unobserved direction handling: Shrunk toward prior, ResultConfidenceTier.PRIOR_ONLY, is_data_backed=False (no 0.5 default).
5. Data-derived batter risk profiles: Replacing KNOWN_BATTER_RISKS with sample-backed, governance-aware features.
6. Integration with real dataset and BatterProfile contracts.
"""
import pytest
import pandas as pd
import numpy as np

from backend.app.services.profiles import Handedness, BatterProfile
from backend.app.services.spatial_intelligence import (
    DIRECTIONS,
    BANDS,
    POPULATION_GLOBAL_RPB,
    POPULATION_EDGE_VS_PACE,
    POPULATION_PULL_MISTIME,
    POPULATION_SWEEP_RISK,
    POPULATION_CHARGE_SPIN,
    POPULATION_LOFTED_DRIVE,
    is_valid_spatial_zone,
    parse_spatial_zone,
    resolve_batter_handedness,
    compute_directional_distribution,
    compute_shrunk_zone_danger,
    derive_batter_risk_profile,
    ResultConfidenceTier,
)
from backend.app.services.real_data_loader import (
    load_deliveries_from_dataframe,
    get_directional_delivery_counts,
    load_all_batters_from_df,
    load_batter_profile_from_real_data,
    get_live_deliveries_df,
)


# ---------------------------------------------------------------------------
# 1. Spatial Zone Domain Validation
# ---------------------------------------------------------------------------

class TestSpatialZoneValidation:
    @pytest.mark.parametrize("valid_input, expected_int", [
        (1, 1),
        (2, 2),
        (3, 3),
        (4, 4),
        (5, 5),
        (6, 6),
        (7, 7),
        (8, 8),
        ("1", 1),
        ("8", 8),
        (1.0, 1),
        (8.0, 8),
        (np.int64(4), 4),
    ])
    def test_valid_spatial_zones(self, valid_input, expected_int):
        assert is_valid_spatial_zone(valid_input) is True
        assert parse_spatial_zone(valid_input) == expected_int

    @pytest.mark.parametrize("invalid_input", [
        0,              # Unavailable spatial data in wagon-wheel datasets
        "0",
        0.0,
        -1,             # Out of bounds
        9,              # Out of bounds
        10,
        "9",
        "-1",
        None,           # Missing / Null
        np.nan,
        "Mid Wicket",   # String direction names are not zone integers
        "Point",
        "",
        "   ",
        2.5,            # Non-integer float
        "2.5",
        [],
        {},
    ])
    def test_invalid_and_unavailable_spatial_zones(self, invalid_input):
        assert is_valid_spatial_zone(invalid_input) is False
        assert parse_spatial_zone(invalid_input) is None


# ---------------------------------------------------------------------------
# 2. Separation of Concerns: Directional vs Outcome Distributions
# ---------------------------------------------------------------------------

class TestDistributionSeparation:
    @pytest.fixture
    def synthetic_spatial_df(self):
        """
        Construct a known test dataset:
        - 10 balls total for 'Test Batter'
        - 2 balls with Zone == 0 (unavailable spatial data, runs: 0, 4)
        - 4 balls to Zone 6 (Cover for RHB, runs: 0, 1, 4, 4 -> 9 runs / 4 balls)
        - 4 balls to Zone 3 (Mid Wicket for RHB, runs: 1, 2, 6, 1 -> 10 runs / 4 balls)
        """
        rows = [
            # Zone 0: Unavailable spatial data (must NOT be counted as shot directions)
            {"Batter": "Test Batter", "Zone": 0, "RunsBatter": 0, "BowlerName": "Bowler A", "Wicket": 0},
            {"Batter": "Test Batter", "Zone": 0, "RunsBatter": 4, "BowlerName": "Bowler A", "Wicket": 0},
            # Zone 6 (Cover for RHB): 4 balls, 9 runs
            {"Batter": "Test Batter", "Zone": 6, "RunsBatter": 0, "BowlerName": "Bowler A", "Wicket": 0},
            {"Batter": "Test Batter", "Zone": 6, "RunsBatter": 1, "BowlerName": "Bowler A", "Wicket": 0},
            {"Batter": "Test Batter", "Zone": 6, "RunsBatter": 4, "BowlerName": "Bowler A", "Wicket": 0},
            {"Batter": "Test Batter", "Zone": 6, "RunsBatter": 4, "BowlerName": "Bowler A", "Wicket": 0},
            # Zone 3 (Mid Wicket for RHB): 4 balls, 10 runs
            {"Batter": "Test Batter", "Zone": 3, "RunsBatter": 1, "BowlerName": "Bowler A", "Wicket": 0},
            {"Batter": "Test Batter", "Zone": 3, "RunsBatter": 2, "BowlerName": "Bowler A", "Wicket": 0},
            {"Batter": "Test Batter", "Zone": 3, "RunsBatter": 6, "BowlerName": "Bowler A", "Wicket": 0},
            {"Batter": "Test Batter", "Zone": 3, "RunsBatter": 1, "BowlerName": "Bowler A", "Wicket": 0},
        ]
        return pd.DataFrame(rows)

    def test_directional_distribution_excludes_zone_zero(self, synthetic_spatial_df):
        dist = compute_directional_distribution(synthetic_spatial_df, "Test Batter", Handedness.RHB)
        
        assert dist.total_deliveries == 10
        assert dist.valid_spatial_deliveries == 8
        assert dist.unavailable_spatial_deliveries == 2
        assert dist.data_coverage_pct == 80.0

        # Exactly 4 balls to Cover and 4 to Mid Wicket; 0 to all other directions
        assert dist.directional_counts["Cover"] == 4
        assert dist.directional_counts["Mid Wicket"] == 4
        assert dist.directional_counts["Point"] == 0
        assert dist.directional_counts["Fine Leg"] == 0

        # Probabilities sum to 1.0 strictly over valid deliveries
        probs = dist.directional_probabilities
        assert sum(probs.values()) == pytest.approx(1.0, abs=1e-4)
        assert probs["Cover"] == 0.5
        assert probs["Mid Wicket"] == 0.5
        assert probs["Point"] == 0.0

    def test_directional_distribution_handles_all_unavailable_spatial_data(self):
        df_unavail = pd.DataFrame([
            {"Batter": "Zero Batter", "Zone": 0, "RunsBatter": 1},
            {"Batter": "Zero Batter", "Zone": 0, "RunsBatter": 0},
        ])
        dist = compute_directional_distribution(df_unavail, "Zero Batter", Handedness.RHB)
        assert dist.total_deliveries == 2
        assert dist.valid_spatial_deliveries == 0
        assert dist.unavailable_spatial_deliveries == 2
        assert dist.confidence_tier == ResultConfidenceTier.UNAVAILABLE
        assert dist.data_coverage_pct == 0.0


# ---------------------------------------------------------------------------
# 3. Statistical Shrinkage (Empirical Bayes)
# ---------------------------------------------------------------------------

class TestEmpiricalBayesShrinkage:
    def test_unobserved_zone_receives_prior_not_hardcoded_0_5(self):
        """
        When a batter has no deliveries in a given sector, the danger must shrink
        to the batter's empirical valid-spatial prior (or population prior), NOT an
        arbitrary magic number like 0.5.
        """
        # Batter only has balls in Zone 6, with average runs = 2.0 (4 balls, 8 runs)
        df = pd.DataFrame([
            {"Batter": "Cover Specialist", "Zone": 6, "RunsBatter": 2},
            {"Batter": "Cover Specialist", "Zone": 6, "RunsBatter": 2},
            {"Batter": "Cover Specialist", "Zone": 6, "RunsBatter": 2},
            {"Batter": "Cover Specialist", "Zone": 6, "RunsBatter": 2},
        ])
        chart, estimates = compute_shrunk_zone_danger(df, "Cover Specialist", Handedness.RHB, prior_strength=20.0)

        # Baseline empirical prior for this batter is 2.0 (8 runs / 4 balls)
        mu_0 = 2.0
        point_est = estimates["Point"]
        assert point_est.sample_count == 0
        assert point_est.raw_runs_per_ball is None
        assert point_est.shrunk_runs_per_ball == pytest.approx(mu_0, abs=0.01)
        assert point_est.confidence_tier == ResultConfidenceTier.PRIOR_ONLY
        assert point_est.is_data_backed is False

        # In the 24-key chart, Point_Inner/Mid/Deep should equal mu_0 (2.0), NOT 0.5!
        assert chart["Point_Inner"] == pytest.approx(mu_0, abs=0.01)
        assert chart["Point_Inner"] != 0.5

    def test_small_sample_shrinks_strongly_toward_prior(self):
        """
        A single 6 in Fine Leg (n=1, S=6) must not produce an ungrounded 6.0 runs/ball danger.
        It should be pulled toward the prior.
        """
        # Overall 10 balls: 9 balls in other zones with 9 runs (1.0 RPB), 1 ball in Fine Leg with 6 runs.
        # Total valid runs = 15 over 10 balls -> mu_0 = 1.5 RPB.
        rows = [{"Batter": "Slugger", "Zone": 5, "RunsBatter": 1} for _ in range(9)]
        rows.append({"Batter": "Slugger", "Zone": 1, "RunsBatter": 6})  # Zone 1 is Fine Leg for RHB
        df = pd.DataFrame(rows)

        chart, estimates = compute_shrunk_zone_danger(df, "Slugger", Handedness.RHB, prior_strength=20.0)
        fl_est = estimates["Fine Leg"]
        assert fl_est.sample_count == 1
        assert fl_est.raw_runs_per_ball == 6.0
        
        # Posterior RPB = (6 + 20 * 1.5) / (1 + 20) = 36 / 21 ≈ 1.714
        assert fl_est.shrunk_runs_per_ball == pytest.approx(36.0 / 21.0, abs=0.01)
        assert fl_est.shrunk_runs_per_ball < 2.0  # Much safer than raw 6.0!
        assert fl_est.confidence_tier == ResultConfidenceTier.DERIVED

    def test_large_sample_approaches_empirical_mean(self):
        """
        With abundant data (e.g. 100 balls in a sector), posterior danger should
        closely track the observed sample mean.
        """
        # 100 balls in Zone 6 (Cover) scoring 200 runs (raw RPB = 2.0)
        rows = [{"Batter": "Master", "Zone": 6, "RunsBatter": 2} for _ in range(100)]
        df = pd.DataFrame(rows)

        chart, estimates = compute_shrunk_zone_danger(df, "Master", Handedness.RHB, prior_strength=20.0)
        cov_est = estimates["Cover"]
        assert cov_est.sample_count == 100
        assert cov_est.raw_runs_per_ball == 2.0
        assert cov_est.shrunk_runs_per_ball == pytest.approx(2.0, abs=0.01)
        assert cov_est.confidence_tier == ResultConfidenceTier.OBSERVED


# ---------------------------------------------------------------------------
# 4. Data-Derived Batter Risk Profiles (Replacing KNOWN_BATTER_RISKS)
# ---------------------------------------------------------------------------

class TestDerivedBatterRisks:
    def test_derive_batter_profile_from_real_dataset(self):
        """Verify that profiles derived for bundled real batters have realistic values and metadata."""
        df = get_live_deliveries_df()
        assert df is not None

        profile_kohli = derive_batter_risk_profile(df, "Virat Kohli")
        assert profile_kohli.batter_name == "Virat Kohli"
        assert profile_kohli.handedness == Handedness.RHB
        assert profile_kohli.total_balls > 1000
        assert profile_kohli.valid_spatial_balls > 800
        assert profile_kohli.overall_tier == ResultConfidenceTier.OBSERVED

        # Check Kohli's pace edge risk is derived and within plausible bounds
        assert 0.35 <= profile_kohli.edge_vs_pace <= 0.65
        edge_meta = profile_kohli.features_metadata["edge_vs_pace"]
        assert edge_meta.sample_size > 400
        assert edge_meta.is_fallback is False
        assert edge_meta.confidence_tier == ResultConfidenceTier.OBSERVED

        # Check all 5 required tactical features exist
        for feat in ["edge_vs_pace", "pull_mistime_vs_short_ball", "sweep_risk_vs_spin", "charge_vs_spin", "lofted_drive_risk"]:
            assert feat in profile_kohli.features_metadata
            val = getattr(profile_kohli, feat)
            assert 0.0 <= val <= 1.0

    def test_left_handed_batters_resolve_correctly(self):
        """Confirm Warner, Gayle, and Sangakkara are resolved as LHB from data or career reference."""
        df = get_live_deliveries_df()
        assert df is not None

        for lhb_name in ["David Warner", "Chris Gayle", "Kumar Sangakkara"]:
            prof = derive_batter_risk_profile(df, lhb_name)
            assert prof.handedness == Handedness.LHB, f"Expected LHB for {lhb_name}, got {prof.handedness}"

    def test_unknown_batter_falls_back_to_prior_gracefully(self):
        """Unknown batter with zero deliveries must receive documented population priors with PRIOR_ONLY tier."""
        empty_df = pd.DataFrame(columns=["Batter", "BowlerName", "RunsBatter", "Zone", "Wicket"])
        prof = derive_batter_risk_profile(empty_df, "Unknown Rookie")
        
        assert prof.batter_name == "Unknown Rookie"
        assert prof.handedness == Handedness.RHB
        assert prof.edge_vs_pace == POPULATION_EDGE_VS_PACE
        assert prof.pull_mistime_vs_short_ball == POPULATION_PULL_MISTIME
        assert prof.sweep_risk_vs_spin == POPULATION_SWEEP_RISK
        assert prof.charge_vs_spin == POPULATION_CHARGE_SPIN
        assert prof.lofted_drive_risk == POPULATION_LOFTED_DRIVE
        assert prof.overall_tier == ResultConfidenceTier.PRIOR_ONLY

        for feat_record in prof.features_metadata.values():
            assert feat_record.confidence_tier == ResultConfidenceTier.PRIOR_ONLY
            assert feat_record.is_fallback is True
            assert feat_record.sample_size == 0


# ---------------------------------------------------------------------------
# 5. Loader Integration and BatterProfile Compatibility
# ---------------------------------------------------------------------------

class TestLoaderIntegration:
    def test_load_deliveries_from_dataframe_returns_complete_24_key_chart(self):
        df = get_live_deliveries_df()
        assert df is not None

        chart, handedness = load_deliveries_from_dataframe(df, "Virat Kohli")
        assert handedness == Handedness.RHB
        assert len(chart) == 24  # 8 directions * 3 bands

        for direction in DIRECTIONS:
            for band in BANDS:
                key = f"{direction}_{band}"
                assert key in chart
                assert isinstance(chart[key], float)
                assert chart[key] > 0.0

    def test_get_directional_delivery_counts_integrity(self):
        df = get_live_deliveries_df()
        assert df is not None

        counts = get_directional_delivery_counts(df, "Virat Kohli")
        assert len(counts) == 8
        total_valid = sum(counts.values())
        # Kohli has 948 valid spatial deliveries in the canonical dataset
        assert total_valid == 948

    def test_load_all_batters_from_df_builds_valid_profiles(self):
        df = get_live_deliveries_df()
        assert df is not None

        profiles = load_all_batters_from_df(df)
        assert len(profiles) == 9

        for p in profiles:
            assert isinstance(p, BatterProfile)
            assert len(p.zone_chart) == 24
            assert 0.0 <= p.edge_vs_pace <= 1.0
            assert 0.0 <= p.pull_mistime_vs_short_ball <= 1.0
            assert 0.0 <= p.sweep_risk_vs_spin <= 1.0
            assert 0.0 <= p.charge_vs_spin <= 1.0
            assert 0.0 <= p.lofted_drive_risk <= 1.0
            assert "Derived from real delivery dataset" in p.notes
            assert "intelligence_metadata" in dir(p)
            assert p.intelligence_metadata.get("batter_name") == p.name
