"""
live_match_engine.py — Real-time stateful ball-by-ball delivery ingestion and dynamic field re-mapping engine.
"""
from __future__ import annotations
import copy
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

from backend.app.services.profiles import (
    BatterProfile,
    BowlerProfile,
    FieldPlacement,
    FielderProfile,
    MatchPhase,
    MatchFormat,
    get_sample_batters,
    get_sample_bowlers,
    get_sample_fielders,
    get_keeper,
    get_phase_from_over,
    resolve_bowler_profile,
    resolve_batter_profile
)
from backend.app.services.real_data_loader import (
    load_batter_profile_from_real_data,
    get_all_available_batters,
    DIRECTIONS,
    BANDS
)
from backend.app.services.optimizer import recommend_field
from backend.app.services.rules_engine import validate_field, get_outside_circle_cap
from backend.app.services.metrics import compute_ers, compute_ewo, compute_cds
from backend.app.services.environmental_engine import EnvironmentalConditions, PitchPhysicsEngine
from backend.app.services.ground_geometry import GroundGeometryEngine
from backend.app.services.ml_prediction_engine import compute_ml_matchup_prediction
from backend.app.services.matchup_engine import analyze_matchup


class LiveMatchSession:
    def __init__(
        self,
        session_id: str = "default",
        batter_name: str = "Virat Kohli",
        bowler_name: str = "Mohammad Asif",
        match_format: MatchFormat = MatchFormat.ODI,
        over: int = 0,
        ball: int = 0,
        runs: int = 0,
        wickets: int = 0,
        tactical_objective: str = "attack_wicket",
        ground_preset_id: str = "standard",
        environmental_conditions: Optional[EnvironmentalConditions] = None
    ):
        self.session_id = session_id
        self.batter_name = batter_name
        self.bowler_name = bowler_name
        self.match_format = match_format
        self.over = over
        self.ball = ball
        self.runs = runs
        self.wickets = wickets
        self.tactical_objective = tactical_objective
        self.ground_preset_id = ground_preset_id
        self.environmental_conditions = environmental_conditions or EnvironmentalConditions()

        self.live_zone_chart = self._initialize_zone_chart()
        self.deliveries_history: List[Dict[str, Any]] = []
        self.undo_stack: List[Dict[str, Any]] = []
        self.last_commentary: str = "Tactical field initialized for active matchup."
        self.last_placements: List[FieldPlacement] = []
        self.last_metrics: Dict[str, Any] = {}

    def _initialize_zone_chart(self) -> Dict[str, float]:
        batter = resolve_batter_profile(self.batter_name)
        if batter is None:
            raise ValueError(f"Batter '{self.batter_name}' not found in active dataset or sample profiles.")
        
        base_chart = getattr(batter, 'zone_chart', {})
        chart: Dict[str, float] = {}
        for d in DIRECTIONS:
            for b in BANDS:
                k = f"{d}_{b}"
                chart[k] = float(base_chart.get(k, 0.5))
        return chart

    def save_snapshot(self) -> None:
        snapshot = {
            "over": self.over,
            "ball": self.ball,
            "runs": self.runs,
            "wickets": self.wickets,
            "batter_name": self.batter_name,
            "bowler_name": self.bowler_name,
            "live_zone_chart": copy.deepcopy(self.live_zone_chart),
            "deliveries_history": copy.deepcopy(self.deliveries_history),
            "last_commentary": self.last_commentary,
            "last_placements": copy.deepcopy(self.last_placements),
            "last_metrics": copy.deepcopy(self.last_metrics),
        }
        self.undo_stack.append(snapshot)
        if len(self.undo_stack) > 36:
            self.undo_stack.pop(0)

    def undo(self) -> bool:
        if not self.undo_stack:
            return False
        prev = self.undo_stack.pop()
        self.over = prev["over"]
        self.ball = prev["ball"]
        self.runs = prev["runs"]
        self.wickets = prev["wickets"]
        self.batter_name = prev["batter_name"]
        self.bowler_name = prev["bowler_name"]
        self.live_zone_chart = prev["live_zone_chart"]
        self.deliveries_history = prev["deliveries_history"]
        self.last_commentary = f"Reverted last delivery. Score restored to {self.runs}/{self.wickets} (Over {self.over}.{self.ball})."
        self.last_placements = prev["last_placements"]
        self.last_metrics = prev["last_metrics"]
        return True

    def reset(
        self,
        batter_name: Optional[str] = None,
        bowler_name: Optional[str] = None,
        match_format: Optional[MatchFormat] = None,
        starting_over: int = 0,
        starting_ball: int = 0,
        starting_runs: int = 0,
        starting_wickets: int = 0,
        tactical_objective: Optional[str] = None,
        ground_preset_id: Optional[str] = None,
        environmental_conditions: Optional[EnvironmentalConditions] = None
    ) -> None:
        if batter_name:
            self.batter_name = batter_name
        if bowler_name:
            self.bowler_name = bowler_name
        if match_format:
            self.match_format = match_format
        self.over = starting_over
        self.ball = starting_ball
        self.runs = starting_runs
        self.wickets = starting_wickets
        if tactical_objective:
            self.tactical_objective = tactical_objective
        if ground_preset_id:
            self.ground_preset_id = ground_preset_id
        if environmental_conditions:
            self.environmental_conditions = environmental_conditions

        self.live_zone_chart = self._initialize_zone_chart()
        self.deliveries_history = []
        self.undo_stack = []
        self.last_commentary = f"Match state reset. Active matchup: {self.batter_name} vs {self.bowler_name}."

    def update_zone_danger(self, sector: str, band: str, runs_batter: int, is_extra: bool) -> str:
        zone_key = f"{sector}_{band}"
        if zone_key not in self.live_zone_chart:
            self.live_zone_chart[zone_key] = 0.5

        cur = self.live_zone_chart[zone_key]
        adjustment_note = ""

        if runs_batter >= 4:
            step = 0.40 if runs_batter == 4 else 0.65
            new_val = min(4.8, cur + step)
            self.live_zone_chart[zone_key] = round(new_val, 3)
            adj_key = f"{sector}_Mid" if band == "Deep" else f"{sector}_Deep"
            if adj_key in self.live_zone_chart:
                self.live_zone_chart[adj_key] = round(min(4.5, self.live_zone_chart[adj_key] + 0.20), 3)
            adjustment_note = f"Boundary scored through {sector}. Dispatched boundary cover; plugged gap."

        elif runs_batter in (1, 2, 3):
            new_val = min(3.2, cur + (0.12 * runs_batter))
            self.live_zone_chart[zone_key] = round(new_val, 3)
            adjustment_note = f"{runs_batter} run(s) through {sector}. Ring fielder shifted to choke single."

        elif runs_batter == 0 and not is_extra:
            new_val = max(0.15, cur - 0.08)
            self.live_zone_chart[zone_key] = round(new_val, 3)
            adjustment_note = f"Dot ball in {sector} channel. Kept pressure ring tight."

        return adjustment_note


class LiveMatchEngine:
    _sessions: Dict[str, LiveMatchSession] = {}

    @classmethod
    def get_session(cls, session_id: str = "default") -> LiveMatchSession:
        if session_id not in cls._sessions:
            cls._sessions[session_id] = LiveMatchSession(session_id=session_id)
        return cls._sessions[session_id]

    @classmethod
    def log_delivery(
        cls,
        session_id: str = "default",
        batter_name: Optional[str] = None,
        bowler_name: Optional[str] = None,
        match_format: Optional[MatchFormat] = None,
        over: Optional[int] = None,
        ball: Optional[int] = None,
        runs_batter: int = 0,
        extras: int = 0,
        extra_type: str = "none",
        shot_sector: str = "Cover",
        shot_band: str = "Deep",
        is_wicket: bool = False,
        wicket_kind: str = "",
        dismissed_player: str = "",
        tactical_objective: Optional[str] = None,
        ground_preset_id: Optional[str] = None,
        environmental_conditions: Optional[EnvironmentalConditions] = None
    ) -> Dict[str, Any]:
        session = cls.get_session(session_id)
        session.save_snapshot()

        if batter_name:
            session.batter_name = batter_name
        if bowler_name:
            session.bowler_name = bowler_name
        if match_format:
            session.match_format = match_format
        if tactical_objective:
            session.tactical_objective = tactical_objective
        if ground_preset_id:
            session.ground_preset_id = ground_preset_id
        if environmental_conditions:
            session.environmental_conditions = environmental_conditions

        if over is not None and over >= 0:
            session.over = over
        if ball is not None and 0 <= ball <= 6:
            session.ball = ball

        delivery_over = session.over
        delivery_ball = session.ball + 1 if session.ball < 6 else 1

        total_runs = runs_batter + extras
        session.runs += total_runs

        if is_wicket:
            session.wickets = min(10, session.wickets + 1)

        is_legal_delivery = extra_type.lower() not in ("wide", "no_ball")
        if is_legal_delivery:
            session.ball += 1
            if session.ball >= 6:
                session.over += 1
                session.ball = 0

        adjustment_note = session.update_zone_danger(
            sector=shot_sector,
            band=shot_band,
            runs_batter=runs_batter,
            is_extra=(not is_legal_delivery)
        )

        if is_wicket:
            w_desc = wicket_kind or "wicket"
            adjustment_note = f"WICKET ({w_desc})! Attacking field cordon strengthened for incoming batter."

        total_legal_balls = (session.over * 6) + session.ball
        crr = round((session.runs / max(1, total_legal_balls)) * 6.0, 2)

        next_over_for_opt = session.over + 1
        next_phase = get_phase_from_over(max(1, next_over_for_opt), session.match_format)

        re_mapped_result = cls._optimize_field_for_state(session, next_over_for_opt, next_phase)

        delivery_record = {
            "delivery_id": str(uuid.uuid4())[:8],
            "over": delivery_over,
            "ball": delivery_ball if is_legal_delivery else delivery_ball - 1,
            "display_over": f"{delivery_over}.{delivery_ball}",
            "batter_name": session.batter_name,
            "bowler_name": session.bowler_name,
            "runs_batter": runs_batter,
            "extras": extras,
            "runs_total": total_runs,
            "extra_type": extra_type,
            "shot_sector": shot_sector,
            "shot_band": shot_band,
            "is_wicket": is_wicket,
            "wicket_kind": wicket_kind if is_wicket else "",
            "tactical_adjustment": adjustment_note,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        session.deliveries_history.append(delivery_record)
        session.last_commentary = adjustment_note

        outside_cap = get_outside_circle_cap(next_phase, session.match_format)
        field_restriction_str = f"Max {outside_cap} Outside 30-Yard Circle ({next_phase.name})"

        return {
            "status": "success",
            "session_id": session.session_id,
            "over": session.over,
            "ball": session.ball,
            "display_over": f"{session.over}.{session.ball}",
            "runs": session.runs,
            "wickets": session.wickets,
            "current_run_rate": crr,
            "phase": next_phase.name,
            "field_restriction": field_restriction_str,
            "tactical_commentary": adjustment_note,
            "zone_chart": session.live_zone_chart,
            "placements": re_mapped_result["placements"],
            "ers": re_mapped_result["ers"],
            "ewo": re_mapped_result["ewo"],
            "cds": re_mapped_result["cds"],
            "is_legal": re_mapped_result["is_legal"],
            "violations": re_mapped_result["violations"],
            "ml_probabilities": re_mapped_result["ml_probabilities"],
            "simulation_metrics": re_mapped_result["simulation_metrics"],
            "pitch_multipliers": re_mapped_result["pitch_multipliers"],
            "delivery_history": session.deliveries_history
        }

    @classmethod
    def undo_delivery(cls, session_id: str = "default") -> Dict[str, Any]:
        session = cls.get_session(session_id)
        success = session.undo()
        if not success:
            return {"status": "error", "message": "No deliveries to undo in active session."}

        next_over_for_opt = session.over + 1
        next_phase = get_phase_from_over(max(1, next_over_for_opt), session.match_format)
        re_mapped_result = cls._optimize_field_for_state(session, next_over_for_opt, next_phase)

        total_legal_balls = (session.over * 6) + session.ball
        crr = round((session.runs / max(1, total_legal_balls)) * 6.0, 2)
        outside_cap = get_outside_circle_cap(next_phase, session.match_format)

        return {
            "status": "success",
            "session_id": session.session_id,
            "over": session.over,
            "ball": session.ball,
            "display_over": f"{session.over}.{session.ball}",
            "runs": session.runs,
            "wickets": session.wickets,
            "current_run_rate": crr,
            "phase": next_phase.name,
            "field_restriction": f"Max {outside_cap} Outside 30-Yard Circle ({next_phase.name})",
            "tactical_commentary": session.last_commentary,
            "zone_chart": session.live_zone_chart,
            "placements": re_mapped_result["placements"],
            "ers": re_mapped_result["ers"],
            "ewo": re_mapped_result["ewo"],
            "cds": re_mapped_result["cds"],
            "is_legal": re_mapped_result["is_legal"],
            "violations": re_mapped_result["violations"],
            "ml_probabilities": re_mapped_result["ml_probabilities"],
            "simulation_metrics": re_mapped_result["simulation_metrics"],
            "pitch_multipliers": re_mapped_result["pitch_multipliers"],
            "delivery_history": session.deliveries_history
        }

    @classmethod
    def reset_session(
        cls,
        session_id: str = "default",
        batter_name: str = "Virat Kohli",
        bowler_name: str = "Mohammad Asif",
        match_format: MatchFormat = MatchFormat.ODI,
        starting_over: int = 0,
        starting_ball: int = 0,
        starting_runs: int = 0,
        starting_wickets: int = 0,
        tactical_objective: str = "attack_wicket",
        ground_preset_id: str = "standard",
        environmental_conditions: Optional[EnvironmentalConditions] = None
    ) -> Dict[str, Any]:
        session = cls.get_session(session_id)
        session.reset(
            batter_name=batter_name,
            bowler_name=bowler_name,
            match_format=match_format,
            starting_over=starting_over,
            starting_ball=starting_ball,
            starting_runs=starting_runs,
            starting_wickets=starting_wickets,
            tactical_objective=tactical_objective,
            ground_preset_id=ground_preset_id,
            environmental_conditions=environmental_conditions
        )

        next_over_for_opt = max(1, starting_over + 1)
        next_phase = get_phase_from_over(next_over_for_opt, match_format)
        re_mapped_result = cls._optimize_field_for_state(session, next_over_for_opt, next_phase)

        outside_cap = get_outside_circle_cap(next_phase, match_format)
        return {
            "status": "success",
            "session_id": session.session_id,
            "over": session.over,
            "ball": session.ball,
            "display_over": f"{session.over}.{session.ball}",
            "runs": session.runs,
            "wickets": session.wickets,
            "current_run_rate": 0.0,
            "phase": next_phase.name,
            "field_restriction": f"Max {outside_cap} Outside 30-Yard Circle ({next_phase.name})",
            "tactical_commentary": session.last_commentary,
            "zone_chart": session.live_zone_chart,
            "placements": re_mapped_result["placements"],
            "ers": re_mapped_result["ers"],
            "ewo": re_mapped_result["ewo"],
            "cds": re_mapped_result["cds"],
            "is_legal": re_mapped_result["is_legal"],
            "violations": re_mapped_result["violations"],
            "ml_probabilities": re_mapped_result["ml_probabilities"],
            "simulation_metrics": re_mapped_result["simulation_metrics"],
            "pitch_multipliers": re_mapped_result["pitch_multipliers"],
            "delivery_history": []
        }

    @classmethod
    def get_live_state(cls, session_id: str = "default") -> Dict[str, Any]:
        session = cls.get_session(session_id)
        next_over_for_opt = max(1, session.over + 1)
        next_phase = get_phase_from_over(next_over_for_opt, session.match_format)
        re_mapped_result = cls._optimize_field_for_state(session, next_over_for_opt, next_phase)

        total_legal_balls = (session.over * 6) + session.ball
        crr = round((session.runs / max(1, total_legal_balls)) * 6.0, 2) if total_legal_balls > 0 else 0.0
        outside_cap = get_outside_circle_cap(next_phase, session.match_format)

        return {
            "status": "success",
            "session_id": session.session_id,
            "over": session.over,
            "ball": session.ball,
            "display_over": f"{session.over}.{session.ball}",
            "runs": session.runs,
            "wickets": session.wickets,
            "current_run_rate": crr,
            "phase": next_phase.name,
            "field_restriction": f"Max {outside_cap} Outside 30-Yard Circle ({next_phase.name})",
            "tactical_commentary": session.last_commentary,
            "zone_chart": session.live_zone_chart,
            "placements": re_mapped_result["placements"],
            "ers": re_mapped_result["ers"],
            "ewo": re_mapped_result["ewo"],
            "cds": re_mapped_result["cds"],
            "is_legal": re_mapped_result["is_legal"],
            "violations": re_mapped_result["violations"],
            "ml_probabilities": re_mapped_result["ml_probabilities"],
            "simulation_metrics": re_mapped_result["simulation_metrics"],
            "pitch_multipliers": re_mapped_result["pitch_multipliers"],
            "delivery_history": session.deliveries_history
        }

    @classmethod
    def _optimize_field_for_state(
        cls,
        session: LiveMatchSession,
        over_number: int,
        phase: MatchPhase
    ) -> Dict[str, Any]:
        batter = resolve_batter_profile(session.batter_name)
        if batter is None:
            raise ValueError(f"Batter '{session.batter_name}' not found in active dataset or sample profiles.")

        active_batter = BatterProfile(
            name=batter.name,
            handedness=batter.handedness,
            zone_chart=copy.deepcopy(session.live_zone_chart),
            edge_vs_pace=batter.edge_vs_pace,
            pull_mistime_vs_short_ball=batter.pull_mistime_vs_short_ball,
            sweep_risk_vs_spin=batter.sweep_risk_vs_spin,
            charge_vs_spin=batter.charge_vs_spin,
            lofted_drive_risk=batter.lofted_drive_risk,
            notes=f"Live session Bayesian updated ({len(session.deliveries_history)} deliveries)"
        )

        bowler = resolve_bowler_profile(session.bowler_name)

        fielders = get_sample_fielders()
        keeper = get_keeper()

        ground = GroundGeometryEngine.get_preset_by_id(session.ground_preset_id)

        result = recommend_field(
            batter=active_batter,
            bowler=bowler,
            fielder_pool=fielders,
            current_over=max(1, over_number),
            fmt=session.match_format,
            keeper=keeper
        )

        for p in result.placements:
            sx, sy = GroundGeometryEngine.snap_fielder_to_boundary(p.x, p.y, ground)
            p.x = sx
            p.y = sy

        is_legal, violations = validate_field(result.placements, phase, session.match_format)

        is_pace = bowler.bowler_type.name in ["RIGHT_ARM_FAST", "LEFT_ARM_FAST", "RIGHT_ARM_MEDIUM"]
        pitch_mults = PitchPhysicsEngine.compute_condition_multipliers(session.environmental_conditions, is_pace)

        ml_probs, sim_metrics = compute_ml_matchup_prediction(
            batter=active_batter,
            bowler=bowler,
            phase=phase,
            placements=result.placements,
            match_format=session.match_format.value,
            objective=session.tactical_objective,
            environmental_conditions=session.environmental_conditions,
            ground_preset_id=ground.id
        )

        placements_schema = [
            {
                "position_name": p.position_name,
                "fielder": {
                    "name": p.fielder.name,
                    "jump": p.fielder.jump,
                    "catching": p.fielder.catching,
                    "arm": p.fielder.arm,
                    "close_in_skill": p.fielder.close_in_skill,
                    "boundary_skill": p.fielder.boundary_skill,
                    "preferred_positions": p.fielder.preferred_positions
                },
                "x": round(p.x, 1),
                "y": round(p.y, 1),
                "role": p.role,
                "reason": p.reason
            }
            for p in result.placements
        ]

        session.last_placements = result.placements

        return {
            "placements": placements_schema,
            "ers": round(result.ers, 2),
            "ewo": round(result.ewo, 2),
            "cds": round(result.cds, 2),
            "is_legal": is_legal,
            "violations": violations,
            "ml_probabilities": {
                "dot_pct": ml_probs.dot_pct,
                "single_pct": ml_probs.single_pct,
                "two_pct": ml_probs.two_pct,
                "boundary_pct": ml_probs.boundary_pct,
                "four_pct": ml_probs.four_pct,
                "six_pct": ml_probs.six_pct,
                "wicket_pct": ml_probs.wicket_pct,
                "expected_runs_per_ball": ml_probs.expected_runs_per_ball,
                "expected_wickets_per_ball": ml_probs.expected_wickets_per_ball,
            },
            "simulation_metrics": {
                "simulated_deliveries": sim_metrics.simulated_deliveries,
                "simulated_dot_pct": sim_metrics.simulated_dot_pct,
                "simulated_boundary_pct": sim_metrics.simulated_boundary_pct,
                "simulated_wicket_pct": sim_metrics.simulated_wicket_pct,
                "expected_runs_per_over": sim_metrics.expected_runs_per_over,
                "confidence_interval_90_min": sim_metrics.confidence_interval_90_min,
                "confidence_interval_90_max": sim_metrics.confidence_interval_90_max,
                "tactical_utility_score": sim_metrics.tactical_utility_score,
                "fielder_catch_efficiencies": sim_metrics.fielder_catch_efficiencies
            },
            "pitch_multipliers": pitch_mults
        }
