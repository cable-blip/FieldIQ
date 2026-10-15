"""
h2h_stats_engine.py
-------------------
Computes real batter-vs-bowler historical head-to-head statistics and recent form
with strict tiered data-coverage fallbacks.

Fallback Tiers:
  1. Direct H2H (batter vs exact bowler, >= min_balls_direct) -> "direct_h2h"
  2. Batter vs bowler_type in Phase (>= min_balls_type_fallback) -> "vs_bowler_type_phase"
  3. Batter vs bowler_type overall (>= min_balls_type_fallback) -> "vs_bowler_type"
  4. Insufficient data -> "insufficient_data" (returns None for stats, never fabricates values)
"""
from __future__ import annotations

from typing import Dict, Any, Optional
import pandas as pd

from backend.app.services.bowler_style import bowler_style, normalize_bowler_type
from backend.app.services.profiles import get_phase_from_over, MatchFormat


class H2HStatsEngine:
    def __init__(
        self,
        deliveries_df: pd.DataFrame,
        min_balls_direct: int = 15,
        min_balls_type_fallback: int = 30,
    ):
        self.df = deliveries_df.copy()
        self.min_balls_direct = min_balls_direct
        self.min_balls_type_fallback = min_balls_type_fallback

        # Normalize column names if needed
        batter_col = next((c for c in self.df.columns if c.lower() in ["batter", "batsman"]), "Batter")
        bowler_col = next((c for c in self.df.columns if c.lower() in ["bowlername", "bowler_name", "bowler"]), "BowlerName")
        runs_col = next((c for c in self.df.columns if c.lower() in ["runsbatter", "runs_batter", "runs"]), "RunsBatter")
        wicket_col = next((c for c in self.df.columns if c.lower() in ["wicket", "is_wicket"]), "Wicket")
        over_col = next((c for c in self.df.columns if c.lower() in ["over"]), "Over")
        game_id_col = next((c for c in self.df.columns if c.lower() in ["gameid", "game_id", "match_id"]), "GameId")

        # Rename to canonical columns internally for consistent queries
        rename_dict = {}
        if batter_col != "Batter": rename_dict[batter_col] = "Batter"
        if bowler_col != "BowlerName": rename_dict[bowler_col] = "BowlerName"
        if runs_col != "RunsBatter": rename_dict[runs_col] = "RunsBatter"
        if wicket_col != "Wicket": rename_dict[wicket_col] = "Wicket"
        if over_col != "Over": rename_dict[over_col] = "Over"
        if game_id_col != "GameId": rename_dict[game_id_col] = "GameId"

        if rename_dict:
            self.df.rename(columns=rename_dict, inplace=True)

        # Ensure boolean Wicket
        if "Wicket" in self.df.columns:
            self.df["Wicket"] = self.df["Wicket"].apply(
                lambda w: bool(w) and str(w).lower() not in ("false", "0")
            )

        # Pre-attach bowler_type if not present
        if "bowler_type" not in self.df.columns:
            self.df["bowler_type"] = self.df["BowlerName"].apply(bowler_style)

        # Pre-attach bowler_discipline if not present
        if "bowler_discipline" not in self.df.columns and "BowlerName" in self.df.columns:
            from backend.app.services.bowler_style import resolve_bowler_discipline
            self.df["bowler_discipline"] = self.df["BowlerName"].apply(
                lambda b: resolve_bowler_discipline(b)[0]
            )

        # Pre-attach phase if Over present
        if "phase" not in self.df.columns and "Over" in self.df.columns:
            def _calc_phase(over_val):
                try:
                    over_num = int(float(over_val)) + 1
                    return get_phase_from_over(over_num, MatchFormat.T20).name
                except (ValueError, TypeError):
                    return "POWERPLAY"
            self.df["phase"] = self.df["Over"].apply(_calc_phase)

    def get_matchup_stats(
        self,
        batter: str,
        bowler: str,
        bowler_type: Optional[str] = None,
        phase: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Returns matchup statistics for a batter vs bowler/type with strict fallback tiers.
        """
        bowler_type = normalize_bowler_type(bowler_type if bowler_type and bowler_type != "Unknown" else bowler)

        source = None
        sub = pd.DataFrame()
        note = ""

        # Tier 1: Direct H2H
        direct_sub = self.df[(self.df["Batter"] == batter) & (self.df["BowlerName"] == bowler)]
        if len(direct_sub) >= self.min_balls_direct:
            source = "direct_h2h"
            sub = direct_sub
            note = f"Direct matchup: {len(sub)} balls faced vs {bowler}"

        # Tier 2: Batter vs bowler_type IN THIS PHASE
        if source is None and phase and bowler_type != "Unknown":
            phase_sub = self.df[
                (self.df["Batter"] == batter)
                & (self.df["bowler_type"] == bowler_type)
                & (self.df["phase"] == phase)
            ]
            if len(phase_sub) >= self.min_balls_type_fallback:
                source = "vs_bowler_type_phase"
                sub = phase_sub
                note = f"Fallback tier 2: {len(sub)} balls faced vs {bowler_type} in {phase} phase"

        # Tier 3: Batter vs bowler_type (any phase)
        if source is None and bowler_type != "Unknown":
            type_sub = self.df[
                (self.df["Batter"] == batter) & (self.df["bowler_type"] == bowler_type)
            ]
            if len(type_sub) >= self.min_balls_type_fallback:
                source = "vs_bowler_type"
                sub = type_sub
                note = f"Fallback tier 3: {len(sub)} balls faced vs {bowler_type} bowlers overall"

        # Tier 4: Insufficient data
        if source is None:
            direct_count = len(direct_sub)
            return {
                "source": "insufficient_data",
                "balls_faced": direct_count,
                "average": None,
                "strike_rate": None,
                "dismissal_rate": None,
                "boundary_pct": None,
                "dot_pct": None,
                "data_coverage_note": f"Insufficient data: only {direct_count} direct balls faced vs {bowler} (threshold: {self.min_balls_direct}) and insufficient bowler_type history.",
            }

        balls_faced = len(sub)
        runs_scored = int(sub["RunsBatter"].sum())
        dismissals = int(sub["Wicket"].sum())

        average = round(runs_scored / dismissals, 2) if dismissals > 0 else None
        strike_rate = round((runs_scored / balls_faced) * 100, 2) if balls_faced > 0 else None
        dismissal_rate = round(dismissals / balls_faced, 4) if balls_faced > 0 else None

        boundaries = int((sub["RunsBatter"].isin([4, 6])).sum())
        dots = int(((sub["RunsBatter"] == 0) & (~sub["Wicket"])).sum())

        boundary_pct = round((boundaries / balls_faced) * 100, 2) if balls_faced > 0 else None
        dot_pct = round((dots / balls_faced) * 100, 2) if balls_faced > 0 else None

        return {
            "source": source,
            "balls_faced": balls_faced,
            "average": average,
            "strike_rate": strike_rate,
            "dismissal_rate": dismissal_rate,
            "boundary_pct": boundary_pct,
            "dot_pct": dot_pct,
            "data_coverage_note": note,
        }

    def _apply_empirical_shrinkage(
        self,
        sample_chart: dict[str, float],
        prior_chart: dict[str, float],
        n_sample: int,
        k: float = 40.0,
    ) -> dict[str, float]:
        """
        Applies empirical Bayesian shrinkage:
          lambda = n_sample / (n_sample + k)
          shrunk[zone] = lambda * sample[zone] + (1 - lambda) * prior[zone]
        Guarantees small samples (e.g. 15-20 balls) do not collapse unhit zones to neutral defaults,
        while large samples smoothly transition to data-driven empirical weights.
        """
        if not prior_chart or n_sample <= 0:
            return sample_chart
        lmbda = float(n_sample) / float(n_sample + k)
        shrunk = {}
        for zk in prior_chart:
            # If the zone wasn't in sample_chart or was neutral default 0.5, use prior
            sample_val = sample_chart.get(zk, prior_chart[zk])
            shrunk[zk] = round(lmbda * sample_val + (1.0 - lmbda) * prior_chart[zk], 3)
        return shrunk

    def get_bowler_conceded_chart(
        self,
        bowler_name: str,
        prior_chart: dict[str, float],
        min_balls_bowler: int = 25,
        k: float = 40.0,
    ) -> tuple[Optional[dict[str, float]], int]:
        """
        Derives the bowler's individual conceded scoring-zone distribution across all batters in the dataset,
        normalized for batter handedness (RHB vs LHB).
        """
        from backend.app.services.real_data_loader import (
            ZONE_TO_DIRECTION_RHB,
            ZONE_TO_DIRECTION_LHB,
            band_from_runs,
            DIRECTIONS,
            BANDS,
        )
        b_df = self.df[self.df["BowlerName"] == bowler_name]
        n = len(b_df)
        if n < min_balls_bowler:
            return None, n

        LHB_SET = {"Kumar Sangakkara", "David Warner", "Chris Gayle"}

        zone_runs = {f"{d}_{b}": [] for d in DIRECTIONS for b in BANDS}
        for _, row in b_df.iterrows():
            runs = int(row["RunsBatter"]) if pd.notna(row.get("RunsBatter")) else 0
            z_val = row.get("Zone")
            direction = None
            try:
                z_num = int(float(z_val))
                if 1 <= z_num <= 8:
                    if row.get("Batter") in LHB_SET:
                        direction = ZONE_TO_DIRECTION_LHB.get(z_num)
                    else:
                        direction = ZONE_TO_DIRECTION_RHB.get(z_num)
            except Exception:
                pass

            if direction:
                band = band_from_runs(runs)
                zone_runs[f"{direction}_{band}"].append(float(runs))

        lmbda = float(n) / float(n + k)
        shrunk = {}
        for zk in prior_chart:
            runs_list = zone_runs.get(zk, [])
            sample_val = (sum(runs_list) / len(runs_list)) if runs_list else prior_chart[zk]
            shrunk[zk] = round(lmbda * sample_val + (1.0 - lmbda) * prior_chart[zk], 3)

        return shrunk, n

    def get_matchup_zone_chart(
        self,
        batter: str,
        bowler: str,
        bowler_type: Optional[str] = None,
        phase: Optional[str] = None,
        batter_prior_chart: Optional[dict[str, float]] = None,
    ) -> tuple[Optional[dict[str, float]], str]:
        """
        Computes matchup-conditioned zone danger weights from real delivery wagon wheels,
        applying Empirical Bayesian shrinkage toward the prior and blending the individual
        bowler's conceded distribution when available.
        """
        from backend.app.services.real_data_loader import load_deliveries_from_dataframe

        # Resolve batter prior chart if not passed
        if not batter_prior_chart:
            from backend.app.services.profiles import resolve_batter_profile
            bp = resolve_batter_profile(batter)
            batter_prior_chart = getattr(bp, "zone_chart", {}) if bp else {}

        # Tier 1: Direct matchup (>= min_balls_direct balls faced)
        direct_sub = self.df[(self.df["Batter"] == batter) & (self.df["BowlerName"] == bowler)]
        n_direct = len(direct_sub)
        if n_direct >= self.min_balls_direct:
            try:
                raw_chart, _ = load_deliveries_from_dataframe(direct_sub, batter)
                shrunk_chart = self._apply_empirical_shrinkage(
                    raw_chart, batter_prior_chart, n_direct, k=40.0
                )
                return shrunk_chart, f"direct_h2h (n={n_direct})"
            except Exception:
                pass

        # Normalize bowler discipline/type string
        disc = str(bowler_type).strip() if bowler_type else ""
        if disc.startswith("BowlerType."):
            disc = disc.replace("BowlerType.", "")

        # Compute bowler conceded profile across all batters if bowler has >= 25 balls
        bowler_conceded_chart, n_bowler = self.get_bowler_conceded_chart(bowler, batter_prior_chart)

        # Tier 2: Batter vs Bowler Discipline in Phase
        if phase and disc and "bowler_discipline" in self.df.columns:
            phase_sub = self.df[
                (self.df["Batter"] == batter)
                & (self.df["bowler_discipline"] == disc)
                & (self.df["phase"] == phase)
            ]
            n_phase = len(phase_sub)
            if n_phase >= self.min_balls_type_fallback:
                try:
                    raw_phase, _ = load_deliveries_from_dataframe(phase_sub, batter)
                    shrunk_phase = self._apply_empirical_shrinkage(
                        raw_phase, batter_prior_chart, n_phase, k=40.0
                    )
                    if bowler_conceded_chart is not None:
                        blended = {
                            zk: round(0.70 * shrunk_phase[zk] + 0.30 * bowler_conceded_chart[zk], 3)
                            for zk in batter_prior_chart
                        }
                        return blended, f"vs_bowler_type_phase_blended (n_type={n_phase}, n_bowler={n_bowler})"
                    return shrunk_phase, f"vs_bowler_type_phase (n={n_phase})"
                except Exception:
                    pass

        # Tier 3: Batter vs Bowler Discipline overall
        if disc and "bowler_discipline" in self.df.columns:
            disc_sub = self.df[
                (self.df["Batter"] == batter)
                & (self.df["bowler_discipline"] == disc)
            ]
            n_type = len(disc_sub)
            if n_type >= self.min_balls_type_fallback:
                try:
                    raw_disc, _ = load_deliveries_from_dataframe(disc_sub, batter)
                    shrunk_disc = self._apply_empirical_shrinkage(
                        raw_disc, batter_prior_chart, n_type, k=40.0
                    )
                    if bowler_conceded_chart is not None:
                        blended = {
                            zk: round(0.70 * shrunk_disc[zk] + 0.30 * bowler_conceded_chart[zk], 3)
                            for zk in batter_prior_chart
                        }
                        return blended, f"vs_bowler_type_blended (n_type={n_type}, n_bowler={n_bowler})"
                    return shrunk_disc, f"vs_bowler_type (n={n_type})"
                except Exception:
                    pass

        # Tier 4: Bowler Conceded Only (bowler has >= 25 balls, but batter lacks discipline history)
        if bowler_conceded_chart is not None and batter_prior_chart:
            blended = {
                zk: round(0.70 * batter_prior_chart[zk] + 0.30 * bowler_conceded_chart[zk], 3)
                for zk in batter_prior_chart
            }
            return blended, f"bowler_concede_blended (n_bowler={n_bowler})"

        return None, "insufficient_data"

    def get_recent_form(
        self,
        batter: str,
        n_balls: int = 10,
        before_game_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Returns strike_rate and dismissal count over the batter's last n_balls faced,
        optionally excluding deliveries from or after before_game_id.
        """
        df_batter = self.df[self.df["Batter"] == batter]
        if before_game_id is not None:
            df_batter = df_batter[df_batter["GameId"] < before_game_id]

        if len(df_batter) == 0:
            return {
                "balls_faced": 0,
                "strike_rate": None,
                "dismissals": 0,
            }

        recent = df_batter.tail(n_balls)
        balls_faced = len(recent)
        runs = int(recent["RunsBatter"].sum())
        dismissals = int(recent["Wicket"].sum())
        sr = round((runs / balls_faced) * 100, 2) if balls_faced > 0 else None

        return {
            "balls_faced": balls_faced,
            "strike_rate": sr,
            "dismissals": dismissals,
        }


_H2H_INSTANCE: Optional[H2HStatsEngine] = None


def get_h2h_stats_engine() -> H2HStatsEngine:
    """Returns singleton H2HStatsEngine instantiated from real deliveries dataset."""
    global _H2H_INSTANCE
    if _H2H_INSTANCE is None:
        from backend.app.services.real_data_loader import get_live_deliveries_df
        df = get_live_deliveries_df()
        if df is None or df.empty:
            df = pd.DataFrame(columns=["Batter", "BowlerName", "RunsBatter", "Wicket", "Over", "GameId"])
        _H2H_INSTANCE = H2HStatsEngine(df)
    return _H2H_INSTANCE


def reset_h2h_stats_engine() -> None:
    """Resets cached H2HStatsEngine instance for testing or data reload."""
    global _H2H_INSTANCE
    _H2H_INSTANCE = None
