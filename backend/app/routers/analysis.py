from fastapi import APIRouter, status, HTTPException
import pandas as pd
from typing import List, Dict, Any, Optional

from backend.app.schemas.analysis import (
    AnalysisRequest,
    AnalysisResponse,
    MatchFormat,
    TacticalObjective,
    FieldPlacementSchema,
    FielderProfileSchema,
    AlternativeFieldSchema,
    EvaluateFieldRequest,
    EvaluateFieldResponse,
    MLOutcomeProbabilitiesSchema,
    SimulationMetricsSchema,
    BatterFormatRecordSchema,
    GroundDimensionPresetSchema,
    GameplanRequestSchema,
    GameplanResponseSchema,
    OverPlanSchema,
    LiveDeliveryRequest,
    LiveDeliveryResponse,
    LiveMatchResetRequest,
    LoggedDeliveryItem,
    MatchupStatsSchema
)
from backend.app.services.profiles import (
    get_sample_batters,
    get_sample_bowlers,
    get_sample_fielders,
    get_keeper,
    resolve_bowler_profile,
    resolve_batter_profile,
    MatchFormat as ServiceMatchFormat,
    FieldPlacement as ServicePlacement,
    FielderProfile,
    get_phase_from_over
)
from backend.app.services.optimizer import recommend_field
from backend.app.services.simulator import generate_candidate_fields
from backend.app.services.rules_engine import validate_field
from backend.app.services.metrics import compute_ers, compute_ewo, compute_cds
from backend.app.services.ml_prediction_engine import compute_ml_matchup_prediction, MLModelManager
from backend.app.services.environmental_engine import (
    EnvironmentalConditions,
    PitchPhysicsEngine,
    PitchType
)
from backend.app.services.ground_geometry import (
    GroundGeometryEngine,
    GroundDimensionPreset,
    INTERNATIONAL_VENUE_PRESETS
)
from backend.app.services.gameplan_engine import GameplanSequencingEngine
from backend.app.services.real_data_loader import (
    get_available_batters_from_df,
    load_all_batters_from_df,
    get_all_available_batters,
    get_all_available_bowlers,
    load_batter_profile_from_real_data,
    DATA_DIR
)
from backend.app.services.live_match_engine import LiveMatchEngine

router = APIRouter(prefix="/api/v1", tags=["analysis"])


@router.get("/players", status_code=status.HTTP_200_OK)
def get_players_list():
    sample_bowlers = [b.name for b in get_sample_bowlers()]
    real_bowlers = get_all_available_bowlers()
    all_bowlers = sorted(list(set(sample_bowlers + real_bowlers)))
    real_batters = get_all_available_batters()
    batters_list = real_batters if real_batters else [b.name for b in get_sample_batters()]
    return {
        "batters": batters_list,
        "bowlers": all_bowlers if all_bowlers else sample_bowlers,
        "tactical_objectives": [obj.value for obj in TacticalObjective],
        "match_formats": [fmt.value for fmt in MatchFormat],
    }


@router.get("/grounds/presets", response_model=List[GroundDimensionPresetSchema], status_code=status.HTTP_200_OK)
def get_ground_presets():
    """
    Returns list of pre-configured international cricket ground geometries and surface defaults.
    """
    presets = GroundGeometryEngine.get_all_presets()
    return [
        GroundDimensionPresetSchema(
            id=p.id,
            name=p.name,
            city=p.city,
            country=p.country,
            straight_boundary_meters=p.straight_boundary_meters,
            square_off_boundary_meters=p.square_off_boundary_meters,
            square_leg_boundary_meters=p.square_leg_boundary_meters,
            behind_square_meters=p.behind_square_meters,
            typical_pitch_type=p.typical_pitch_type.value,
            description=p.description
        )
        for p in presets
    ]


@router.post(
    "/analysis",
    response_model=AnalysisResponse,
    status_code=status.HTTP_200_OK,
)
def create_analysis_request(
    request: AnalysisRequest,
) -> AnalysisResponse:
    # Resolve match format & phase
    fmt = ServiceMatchFormat.T20 if request.match_format == MatchFormat.T20 else ServiceMatchFormat.ODI
    phase = get_phase_from_over(request.over, fmt)

    # Resolve environmental conditions & ground preset
    env = EnvironmentalConditions.from_dict(request.environmental_conditions.model_dump() if request.environmental_conditions else {})
    ground_id = request.ground_preset_id or "standard"
    ground = GroundGeometryEngine.get_preset_by_id(ground_id)

    # Resolve batter profile (dynamic from real dataset if present, or curated sample)
    batter = resolve_batter_profile(request.batter_name)
    if batter is None:
        raise HTTPException(
            status_code=404,
            detail=f"Batter '{request.batter_name}' not found in active dataset or sample profiles. Valid batters: {get_all_available_batters()}"
        )

    bowler = resolve_bowler_profile(request.bowler_name)

    fielders = get_sample_fielders()
    keeper = get_keeper()

    # Call optimizer for main recommended field
    result = recommend_field(
        batter=batter,
        bowler=bowler,
        fielder_pool=fielders,
        current_over=request.over,
        fmt=fmt,
        keeper=keeper
    )

    # Snap boundary fielders according to ground geometry
    for p in result.placements:
        sx, sy = GroundGeometryEngine.snap_fielder_to_boundary(p.x, p.y, ground)
        p.x = sx
        p.y = sy

    # Convert placements list
    placements_schema = [
        FieldPlacementSchema(
            position_name=p.position_name,
            fielder=FielderProfileSchema(
                name=p.fielder.name,
                jump=p.fielder.jump,
                catching=p.fielder.catching,
                arm=p.fielder.arm,
                close_in_skill=p.fielder.close_in_skill,
                boundary_skill=p.fielder.boundary_skill,
                preferred_positions=p.fielder.preferred_positions
            ),
            x=p.x,
            y=p.y,
            role=p.role,
            reason=p.reason
        )
        for p in result.placements
    ]

    # Generate alternative candidate fields
    raw_alternatives = generate_candidate_fields(
        batter=batter,
        bowler=bowler,
        fielder_pool=fielders,
        current_over=request.over,
        fmt=fmt,
        keeper=keeper
    )

    alt_schemas = []
    for alt in raw_alternatives:
        alt_placements = [
            FieldPlacementSchema(
                position_name=p.position_name,
                fielder=FielderProfileSchema(
                    name=p.fielder.name,
                    jump=p.fielder.jump,
                    catching=p.fielder.catching,
                    arm=p.fielder.arm,
                    close_in_skill=p.fielder.close_in_skill,
                    boundary_skill=p.fielder.boundary_skill,
                    preferred_positions=p.fielder.preferred_positions
                ),
                x=p.x,
                y=p.y,
                role=p.role,
                reason=p.reason
            )
            for p in alt["placements"]
        ]
        alt_schemas.append(
            AlternativeFieldSchema(
                strategy_id=alt["strategy_id"],
                strategy_name=alt["strategy_name"],
                description=alt["description"],
                placements=alt_placements,
                ers=alt["ers"],
                ewo=alt["ewo"],
                cds=alt["cds"]
            )
        )

    # Extract tiered head-to-head matchup statistics from optimizer result
    h2h_data = getattr(result, "h2h_stats", None)
    if h2h_data:
        h2h_stats_schema = MatchupStatsSchema(
            has_history=h2h_data["source"] != "insufficient_data",
            balls_faced=h2h_data["balls_faced"],
            runs_scored=int(h2h_data.get("runs_scored", 0)) if "runs_scored" in h2h_data else 0,
            dismissals=int(round(h2h_data["balls_faced"] * (h2h_data.get("dismissal_rate") or 0))),
            strike_rate=h2h_data.get("strike_rate"),
            dot_ball_pct=h2h_data.get("dot_pct"),
            boundary_pct=h2h_data.get("boundary_pct"),
            source=h2h_data.get("source"),
            data_coverage_note=h2h_data.get("data_coverage_note", ""),
        )
    else:
        from backend.app.services.matchup_stats import get_matchup_stats
        legacy_stats = get_matchup_stats(request.batter_name, request.bowler_name)
        h2h_stats_schema = MatchupStatsSchema(
            has_history=legacy_stats["has_history"],
            balls_faced=legacy_stats["balls_faced"],
            runs_scored=legacy_stats["runs_scored"],
            dismissals=legacy_stats["dismissals"],
            strike_rate=legacy_stats["strike_rate"],
            dot_ball_pct=legacy_stats["dot_ball_pct"],
            boundary_pct=legacy_stats["boundary_pct"],
            source="direct_h2h" if legacy_stats["has_history"] else "insufficient_data",
            data_coverage_note="Direct matchup" if legacy_stats["has_history"] else "No historical records",
        )

    # Execute ML Historical Data-Driven & Monte Carlo Prediction Engine
    is_pace = bowler.bowler_type.name in ["RIGHT_ARM_FAST", "LEFT_ARM_FAST", "RIGHT_ARM_MEDIUM"]
    pitch_mults = PitchPhysicsEngine.compute_condition_multipliers(env, is_pace)

    ml_probs, sim_metrics = compute_ml_matchup_prediction(
        batter=batter,
        bowler=bowler,
        phase=phase,
        placements=result.placements,
        match_format=request.match_format.value,
        objective=request.tactical_objective.value,
        environmental_conditions=env,
        ground_preset_id=ground.id,
        over_num=request.over,
    )

    fmt_rec_schema = None
    if ml_probs.format_record:
        rec = ml_probs.format_record
        fmt_rec_schema = BatterFormatRecordSchema(
            format_name=rec.format_name,
            bowler_type_category=rec.bowler_type_category,
            balls_faced=rec.balls_faced,
            runs_scored=rec.runs_scored,
            dismissals=rec.dismissals,
            batting_average=rec.batting_average,
            strike_rate=rec.strike_rate,
            dot_ball_pct=rec.dot_ball_pct,
            boundary_pct=rec.boundary_pct,
            caught_behind_slips_pct=rec.caught_behind_slips_pct,
            caught_infield_pct=rec.caught_infield_pct,
            caught_deep_boundary_pct=rec.caught_deep_boundary_pct,
            bowled_lbw_pct=rec.bowled_lbw_pct,
            stumped_pct=rec.stumped_pct
        )

    model_confidence_info = MLModelManager.get_wicket_evaluation_metrics()

    ml_probs_schema = MLOutcomeProbabilitiesSchema(
        dot_pct=ml_probs.dot_pct,
        single_pct=ml_probs.single_pct,
        two_pct=ml_probs.two_pct,
        boundary_pct=ml_probs.boundary_pct,
        four_pct=ml_probs.four_pct,
        six_pct=ml_probs.six_pct,
        wicket_pct=ml_probs.wicket_pct,
        expected_runs_per_ball=ml_probs.expected_runs_per_ball,
        expected_wickets_per_ball=ml_probs.expected_wickets_per_ball,
        format_record=fmt_rec_schema,
        model_confidence=model_confidence_info["level"],
        wicket_prediction_recall=model_confidence_info["wicket_prediction_recall"],
        wicket_prediction_precision=model_confidence_info["wicket_prediction_precision"]
    )

    sim_metrics_schema = SimulationMetricsSchema(
        simulated_deliveries=sim_metrics.simulated_deliveries,
        simulated_dot_pct=sim_metrics.simulated_dot_pct,
        simulated_boundary_pct=sim_metrics.simulated_boundary_pct,
        simulated_wicket_pct=sim_metrics.simulated_wicket_pct,
        expected_runs_per_over=sim_metrics.expected_runs_per_over,
        confidence_interval_90_min=sim_metrics.confidence_interval_90_min,
        confidence_interval_90_max=sim_metrics.confidence_interval_90_max,
        tactical_utility_score=sim_metrics.tactical_utility_score,
        fielder_catch_efficiencies=sim_metrics.fielder_catch_efficiencies
    )

    coverage_tier = getattr(result, "data_coverage", "insufficient_data")

    return AnalysisResponse(
        status="available",
        data_driven=True if (load_batter_profile_from_real_data(request.batter_name) is not None) else False,
        reason="Deterministic expert recommendation rules engine with Bayesian ML simulation.",
        placements=placements_schema,
        ers=result.ers,
        ewo=result.ewo,
        cds=result.cds,
        tactical_explanations=result.tactical_explanations,
        is_legal=result.is_legal,
        violations=result.violations,
        matchup_stats=h2h_stats_schema,
        data_coverage=coverage_tier,
        model_confidence=model_confidence_info,
        bowler_provenance=getattr(bowler, "provenance_metadata", None),
        alternative_fields=alt_schemas,
        zone_chart=batter.zone_chart if (batter and getattr(batter, 'zone_chart', None)) else {},
        ml_probabilities=ml_probs_schema,
        simulation_metrics=sim_metrics_schema,
        pitch_multipliers=pitch_mults,
        ground_preset=ground.to_dict(),
        accepted_request=request
    )


@router.post(
    "/analysis/evaluate",
    response_model=EvaluateFieldResponse,
    status_code=status.HTTP_200_OK,
)
def evaluate_custom_field(
    request: EvaluateFieldRequest,
) -> EvaluateFieldResponse:
    fmt = ServiceMatchFormat.T20 if request.match_format == MatchFormat.T20 else ServiceMatchFormat.ODI
    phase = get_phase_from_over(request.over, fmt)
    env = EnvironmentalConditions.from_dict(request.environmental_conditions.model_dump() if request.environmental_conditions else {})
    ground_id = request.ground_preset_id or "standard"
    ground = GroundGeometryEngine.get_preset_by_id(ground_id)

    service_placements = []
    for p in request.placements:
        fp = FielderProfile(
            name=p.fielder.name,
            jump=p.fielder.jump,
            catching=p.fielder.catching,
            arm=p.fielder.arm,
            close_in_skill=p.fielder.close_in_skill,
            boundary_skill=p.fielder.boundary_skill,
            preferred_positions=p.fielder.preferred_positions
        )
        service_placements.append(
            ServicePlacement(
                position_name=p.position_name,
                fielder=fp,
                x=p.x,
                y=p.y,
                role=p.role,
                reason=p.reason
            )
        )

    # Resolve batter & bowler
    batter = resolve_batter_profile(request.batter_name)
    if batter is None:
        raise HTTPException(
            status_code=404,
            detail=f"Batter '{request.batter_name}' not found in active dataset or sample profiles. Valid batters: {get_all_available_batters()}"
        )

    bowler = resolve_bowler_profile(request.bowler_name)

    # Validate legality
    is_legal, violations = validate_field(service_placements, phase, fmt)

    # Compute metrics
    ers = compute_ers(service_placements, batter)
    from backend.app.services.matchup_engine import analyze_matchup
    recs = analyze_matchup(batter, bowler, phase)
    ewo = compute_ewo(service_placements, recs, batter, bowler)
    cds = compute_cds(ers, ewo, phase)

    # Execute ML outcome estimation
    is_pace = bowler.bowler_type.name in ["RIGHT_ARM_FAST", "LEFT_ARM_FAST", "RIGHT_ARM_MEDIUM"]
    pitch_mults = PitchPhysicsEngine.compute_condition_multipliers(env, is_pace)

    ml_probs, sim_metrics = compute_ml_matchup_prediction(
        batter=batter,
        bowler=bowler,
        phase=phase,
        placements=service_placements,
        match_format=request.match_format.value,
        objective="attack_wicket",
        environmental_conditions=env,
        ground_preset_id=ground.id,
        over_num=request.over,
    )

    fmt_rec_schema = None
    if ml_probs.format_record:
        rec = ml_probs.format_record
        fmt_rec_schema = BatterFormatRecordSchema(
            format_name=rec.format_name,
            bowler_type_category=rec.bowler_type_category,
            balls_faced=rec.balls_faced,
            runs_scored=rec.runs_scored,
            dismissals=rec.dismissals,
            batting_average=rec.batting_average,
            strike_rate=rec.strike_rate,
            dot_ball_pct=rec.dot_ball_pct,
            boundary_pct=rec.boundary_pct,
            caught_behind_slips_pct=rec.caught_behind_slips_pct,
            caught_infield_pct=rec.caught_infield_pct,
            caught_deep_boundary_pct=rec.caught_deep_boundary_pct,
            bowled_lbw_pct=rec.bowled_lbw_pct,
            stumped_pct=rec.stumped_pct
        )

    eval_confidence_info = MLModelManager.get_wicket_evaluation_metrics()

    ml_probs_schema = MLOutcomeProbabilitiesSchema(
        dot_pct=ml_probs.dot_pct,
        single_pct=ml_probs.single_pct,
        two_pct=ml_probs.two_pct,
        boundary_pct=ml_probs.boundary_pct,
        four_pct=ml_probs.four_pct,
        six_pct=ml_probs.six_pct,
        wicket_pct=ml_probs.wicket_pct,
        expected_runs_per_ball=ml_probs.expected_runs_per_ball,
        expected_wickets_per_ball=ml_probs.expected_wickets_per_ball,
        format_record=fmt_rec_schema,
        model_confidence=eval_confidence_info["level"],
        wicket_prediction_recall=eval_confidence_info["wicket_prediction_recall"],
        wicket_prediction_precision=eval_confidence_info["wicket_prediction_precision"]
    )

    sim_metrics_schema = SimulationMetricsSchema(
        simulated_deliveries=sim_metrics.simulated_deliveries,
        simulated_dot_pct=sim_metrics.simulated_dot_pct,
        simulated_boundary_pct=sim_metrics.simulated_boundary_pct,
        simulated_wicket_pct=sim_metrics.simulated_wicket_pct,
        expected_runs_per_over=sim_metrics.expected_runs_per_over,
        confidence_interval_90_min=sim_metrics.confidence_interval_90_min,
        confidence_interval_90_max=sim_metrics.confidence_interval_90_max,
        tactical_utility_score=sim_metrics.tactical_utility_score,
        fielder_catch_efficiencies=sim_metrics.fielder_catch_efficiencies
    )

    from backend.app.services.matchup_stats import get_matchup_stats
    eval_h2h = get_matchup_stats(request.batter_name, request.bowler_name)
    eval_coverage = "direct_h2h" if (eval_h2h.get("has_history") and eval_h2h.get("balls_faced", 0) >= 15) else (
        "sparse_h2h" if eval_h2h.get("has_history") else "insufficient_data"
    )

    return EvaluateFieldResponse(
        ers=round(ers, 2),
        ewo=round(ewo, 2),
        cds=round(cds, 2),
        is_legal=is_legal,
        violations=violations,
        data_coverage=eval_coverage,
        model_confidence=eval_confidence_info,
        bowler_provenance=getattr(bowler, "provenance_metadata", None),
        ml_probabilities=ml_probs_schema,
        simulation_metrics=sim_metrics_schema,
        pitch_multipliers=pitch_mults
    )


@router.post(
    "/analysis/gameplan",
    response_model=GameplanResponseSchema,
    status_code=status.HTTP_200_OK
)
def generate_gameplan(
    request: GameplanRequestSchema
) -> GameplanResponseSchema:
    """
    Generates a progressive multi-over tactical bowling and fielding gameplan
    with delivery variation recommendations.
    """
    env = EnvironmentalConditions.from_dict(request.environmental_conditions.model_dump() if request.environmental_conditions else {})
    res = GameplanSequencingEngine.generate_multi_over_gameplan(
        batter_name=request.batter_name,
        bowler_name=request.bowler_name,
        match_format=request.match_format.value,
        current_over=request.current_over,
        runs=request.runs,
        wickets=request.wickets,
        planned_overs=request.planned_overs,
        tactical_objective=request.tactical_objective.value,
        environmental_conditions=env,
        ground_preset_id=request.ground_preset_id or "standard"
    )

    return GameplanResponseSchema(
        status=res["status"],
        batter_name=res["batter_name"],
        bowler_name=res["bowler_name"],
        match_format=res["match_format"],
        ground_preset=res["ground_preset"],
        environmental_conditions=res["environmental_conditions"],
        pitch_multipliers=res["pitch_multipliers"],
        planned_overs_count=res["planned_overs_count"],
        gameplan_sequence=[
            OverPlanSchema(
                over_number=op["over_number"],
                phase=op["phase"],
                tactical_objective=op["tactical_objective"],
                bowler_recommended_channel=op["bowler_recommended_channel"],
                bowler_recommended_length=op["bowler_recommended_length"],
                suggested_variations=op["suggested_variations"],
                tactical_directive=op["tactical_directive"],
                ers=op["ers"],
                ewo=op["ewo"],
                cds=op["cds"],
                is_legal=op["is_legal"],
                placements=op["placements"],
                outcome_probabilities=op["outcome_probabilities"] if isinstance(op.get("outcome_probabilities"), dict) else None,
                simulation_telemetry=op["simulation_telemetry"] if isinstance(op.get("simulation_telemetry"), dict) else None
            )
            for op in res["gameplan_sequence"]
        ]
    )


# ---------------------------------------------------------------------------
# Real-Time Ball-by-Ball Delivery Ingestion & Dynamic Field Re-Mapping Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/match/delivery",
    response_model=LiveDeliveryResponse,
    status_code=status.HTTP_200_OK
)
def log_live_delivery(request: LiveDeliveryRequest) -> LiveDeliveryResponse:
    """
    Ingests a single delivery into the live session, increments match score/ball,
    dynamically elevates/adjusts the batter's wagon wheel sector danger,
    and automatically re-maps the field placements for the next delivery.
    """
    fmt = ServiceMatchFormat.T20 if request.match_format == MatchFormat.T20 else ServiceMatchFormat.ODI
    env = EnvironmentalConditions.from_dict(
        request.environmental_conditions.model_dump() if request.environmental_conditions else {}
    )

    try:
        result = LiveMatchEngine.log_delivery(
            session_id="default",
            batter_name=request.batter_name,
            bowler_name=request.bowler_name,
            match_format=fmt,
            over=request.over,
            ball=request.ball,
            runs_batter=request.runs_batter,
            extras=request.extras,
            extra_type=request.extra_type,
            shot_sector=request.shot_sector,
            shot_band=request.shot_band,
            is_wicket=request.is_wicket,
            wicket_kind=request.wicket_kind or "",
            dismissed_player=request.dismissed_player or "",
            tactical_objective=request.tactical_objective.value,
            ground_preset_id=request.ground_preset_id or "standard",
            environmental_conditions=env
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

    return LiveDeliveryResponse(**result)


@router.get(
    "/match/live",
    response_model=LiveDeliveryResponse,
    status_code=status.HTTP_200_OK
)
def get_live_match_state(session_id: str = "default") -> LiveDeliveryResponse:
    """
    Retrieves the current live session score, active field placements, and recent deliveries.
    """
    result = LiveMatchEngine.get_live_state(session_id=session_id)
    return LiveDeliveryResponse(**result)


@router.post(
    "/match/undo",
    response_model=LiveDeliveryResponse,
    status_code=status.HTTP_200_OK
)
def undo_last_delivery(session_id: str = "default") -> LiveDeliveryResponse:
    """
    Reverts the last logged delivery, restoring the previous score, balls, zone danger, and field.
    """
    result = LiveMatchEngine.undo_delivery(session_id=session_id)
    if result.get("status") == "error":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("message", "Cannot undo delivery.")
        )
    return LiveDeliveryResponse(**result)


@router.post(
    "/match/reset",
    response_model=LiveDeliveryResponse,
    status_code=status.HTTP_200_OK
)
def reset_live_match(request: LiveMatchResetRequest) -> LiveDeliveryResponse:
    """
    Resets the live match session with custom starting score, over, and players.
    """
    fmt = ServiceMatchFormat.T20 if request.match_format == MatchFormat.T20 else ServiceMatchFormat.ODI
    env = EnvironmentalConditions.from_dict(
        request.environmental_conditions.model_dump() if request.environmental_conditions else {}
    )

    try:
        result = LiveMatchEngine.reset_session(
            session_id="default",
            batter_name=request.batter_name or "Virat Kohli",
            bowler_name=request.bowler_name or "Generic Right-Arm Fast (New Ball)",
            match_format=fmt,
            starting_over=request.starting_over,
            starting_ball=request.starting_ball,
            starting_runs=request.starting_runs,
            starting_wickets=request.starting_wickets,
            tactical_objective=request.tactical_objective.value,
            ground_preset_id=request.ground_preset_id or "standard",
            environmental_conditions=env
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

    return LiveDeliveryResponse(**result)