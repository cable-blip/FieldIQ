from typing import Dict, Any, List, Optional
from backend.app.services.profiles import (
    BatterProfile,
    BowlerProfile,
    MatchPhase,
    MatchFormat,
    get_phase_from_over,
    get_sample_batters,
    get_sample_bowlers,
    get_sample_fielders,
    get_keeper,
    resolve_bowler_profile,
    resolve_batter_profile
)
from backend.app.services.real_data_loader import load_batter_profile_from_real_data
from backend.app.services.optimizer import recommend_field
from backend.app.services.ml_prediction_engine import compute_ml_matchup_prediction
from backend.app.services.environmental_engine import (
    EnvironmentalConditions,
    PitchPhysicsEngine,
    PitchType
)
from backend.app.services.ground_geometry import (
    GroundGeometryEngine,
    GroundDimensionPreset
)


class GameplanSequencingEngine:
    """
    Generates a progressive multi-over tactical bowling and fielding gameplan.
    Sequences over-by-over tactical transitions, channel/length adjustments,
    delivery variations, and field morphs.
    """

    @staticmethod
    def generate_multi_over_gameplan(
        batter_name: str,
        bowler_name: str,
        match_format: str,
        current_over: int,
        runs: int,
        wickets: int,
        planned_overs: int = 4,
        tactical_objective: str = "attack_wicket",
        environmental_conditions: Optional[EnvironmentalConditions] = None,
        ground_preset_id: str = "standard"
    ) -> Dict[str, Any]:
        fmt = MatchFormat.T20 if match_format.upper() == "T20" else MatchFormat.ODI
        env = environmental_conditions or EnvironmentalConditions()
        ground = GroundGeometryEngine.get_preset_by_id(ground_preset_id)

        # Resolve batter and bowler
        batter = resolve_batter_profile(batter_name)
        if not batter:
            raise ValueError(f"Batter '{batter_name}' not found in active dataset or sample profiles.")

        bowler = resolve_bowler_profile(bowler_name)

        fielders = get_sample_fielders()
        keeper = get_keeper()

        over_plans: List[Dict[str, Any]] = []
        max_overs = 20 if fmt == MatchFormat.T20 else 50
        num_overs = min(planned_overs, max_overs - current_over + 1)
        if num_overs < 1:
            num_overs = 1

        is_pace = bowler.bowler_type.name in ["RIGHT_ARM_FAST", "LEFT_ARM_FAST", "RIGHT_ARM_MEDIUM"]
        pitch_mults = PitchPhysicsEngine.compute_condition_multipliers(env, is_pace)

        for i in range(num_overs):
            over_num = current_over + i
            phase = get_phase_from_over(over_num, fmt)

            # Determine tactical objective shift across sequence
            phase_objective = tactical_objective
            if phase == MatchPhase.POWERPLAY:
                phase_objective = "attack_wicket" if wickets < 3 else "build_pressure"
            elif phase == MatchPhase.MIDDLE:
                phase_objective = "build_pressure" if i % 2 == 0 else "stop_singles"
            elif phase == MatchPhase.DEATH:
                phase_objective = "prevent_boundary"

            # Compute field recommendation
            field_res = recommend_field(
                batter=batter,
                bowler=bowler,
                fielder_pool=fielders,
                current_over=over_num,
                fmt=fmt,
                keeper=keeper
            )

            # Snap boundary fielders to ground perimeter
            snapped_placements = []
            for p in field_res.placements:
                sx, sy = GroundGeometryEngine.snap_fielder_to_boundary(p.x, p.y, ground)
                p.x = sx
                p.y = sy
                snapped_placements.append(p)

            # Compute ML outcome probabilities
            ml_probs, sim_metrics = compute_ml_matchup_prediction(
                batter=batter,
                bowler=bowler,
                phase=phase,
                placements=snapped_placements,
                format_name=fmt.name,
                environmental_conditions=env,
                ground_preset_id=ground.id
            )

            # Tactical delivery directives
            channel, length, variations, directive = GameplanSequencingEngine._derive_delivery_tactics(
                bowler=bowler,
                batter=batter,
                phase=phase,
                over_index=i,
                pitch_type=env.pitch_type,
                pitch_mults=pitch_mults
            )

            over_plans.append({
                "over_number": over_num,
                "phase": phase.name,
                "tactical_objective": phase_objective,
                "bowler_recommended_channel": channel,
                "bowler_recommended_length": length,
                "suggested_variations": variations,
                "tactical_directive": directive,
                "ers": round(field_res.ers, 2),
                "ewo": round(field_res.ewo, 2),
                "cds": round(field_res.cds, 2),
                "is_legal": field_res.is_legal,
                "placements": [
                    {
                        "position_name": p.position_name,
                        "x": p.x,
                        "y": p.y,
                        "role": p.role,
                        "reason": p.reason,
                        "fielder_name": p.fielder.name
                    }
                    for p in snapped_placements
                ],
                "outcome_probabilities": {
                    "dot_pct": ml_probs.dot_pct,
                    "single_pct": ml_probs.single_pct,
                    "two_pct": ml_probs.two_pct,
                    "boundary_pct": ml_probs.boundary_pct,
                    "four_pct": ml_probs.four_pct,
                    "six_pct": ml_probs.six_pct,
                    "wicket_pct": ml_probs.wicket_pct,
                    "expected_runs_per_ball": ml_probs.expected_runs_per_ball,
                    "expected_wickets_per_ball": ml_probs.expected_wickets_per_ball
                },
                "simulation_telemetry": {
                    "simulated_deliveries": sim_metrics.simulated_deliveries,
                    "expected_runs_per_over": sim_metrics.expected_runs_per_over,
                    "confidence_interval_90_min": sim_metrics.confidence_interval_90_min,
                    "confidence_interval_90_max": sim_metrics.confidence_interval_90_max,
                    "tactical_utility_score": sim_metrics.tactical_utility_score
                }
            })

        return {
            "status": "success",
            "batter_name": batter.name,
            "bowler_name": bowler.name,
            "match_format": fmt.name,
            "ground_preset": ground.to_dict(),
            "environmental_conditions": env.to_dict(),
            "pitch_multipliers": pitch_mults,
            "planned_overs_count": len(over_plans),
            "gameplan_sequence": over_plans
        }

    @staticmethod
    def _derive_delivery_tactics(
        bowler: BowlerProfile,
        batter: BatterProfile,
        phase: MatchPhase,
        over_index: int,
        pitch_type: PitchType,
        pitch_mults: Dict[str, float]
    ) -> tuple[str, str, List[str], str]:
        is_pace = bowler.bowler_type.name in ["RIGHT_ARM_FAST", "LEFT_ARM_FAST", "RIGHT_ARM_MEDIUM"]
        
        if phase == MatchPhase.POWERPLAY:
            if is_pace:
                if pitch_type == PitchType.GREEN_SEAM:
                    return (
                        "Corridor of Uncertainty (4th Stump)",
                        "Good / Full Length (5-6m)",
                        ["Outswinger on 4th stump line", "In-nipper attacking top of off", "Full testing drive bait"],
                        f"Over {over_index + 1}: Exploit fresh {pitch_type.value} surface. Maintain strict 4th-stump channel with 2 Slips to draw outside edge."
                    )
                else:
                    return (
                        "Top of Off Stump",
                        "Good Length (6-7m)",
                        ["Hard length seam-up", "Back of length cramping batter", "Skiddy in-angler"],
                        f"Over {over_index + 1}: Tight stump-to-stump line to restrict powerplay aerial boundaries."
                    )
            else:
                return (
                    "Middle and Off",
                    "Flighted Full (3-4m)",
                    ["Drifting into pads", "Gripping leg-cutter", "Arm ball"],
                    f"Over {over_index + 1}: Flight outside off to tempt lofted drive into inner ring cordon."
                )

        elif phase == MatchPhase.MIDDLE:
            if is_pace:
                return (
                    "Bodyline & Ribcage Channel",
                    "Back of a Length / Short Pitch",
                    ["Heavy ball bouncer (shoulder height)", "Off-cutter into pitch", "Hard length at off stump"],
                    f"Over {over_index + 1}: Push batter back with high bumper trap to Deep Backward Square Leg."
                )
            else:
                if pitch_type == PitchType.DUSTY_SPIN:
                    return (
                        "Outside Off into Rough",
                        "Full / Varied Good Length",
                        ["Sharp turning off-break", "Straighter quicker one", "Floated slower loop"],
                        f"Over {over_index + 1}: Land in rough outside off; spin turn multiplier {pitch_mults.get('spin_turn_multiplier', 1.0)}x brings bat-pad into play."
                    )
                else:
                    return (
                        "Stump to Stump",
                        "Good Length",
                        ["Flatter trajectory", "Drifter", "Slider targeting stumps"],
                        f"Over {over_index + 1}: Containment squeeze to starve boundary access and induce mistimed charge."
                    )

        else: # DEATH
            if is_pace:
                return (
                    "Wide Outside Off Corridor (Tramline)",
                    "Pinpoint Toe-Crushing Yorker / Wide Slower Yorker",
                    ["Wide yorker outside tramline", "Slower ball off-cutter bouncer", "Reverse swing toe-crusher"],
                    f"Over {over_index + 1}: Execute wide yorkers outside batter's hitting arc with 5 boundary riders protecting the rope."
                )
            else:
                return (
                    "Fired Flat at Batter's Legs",
                    "Full Yorker / Darts",
                    ["Flatter dart at pads", "Wide sliding yorker", "High deceptive loop"],
                    f"Over {over_index + 1}: Deny leverage under the ball by firing yorker lengths at the base of stumps."
                )
