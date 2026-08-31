from fastapi import APIRouter, status, HTTPException
import pandas as pd
from typing import List, Dict, Any, Optional

from backend.app.schemas.analysis import (
    AnalysisRequest,
    AnalysisResponse,
    MatchFormat,
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
    OverPlanSchema
)
from backend.app.services.profiles import (
    get_sample_batters,
    get_sample_bowlers,
    get_sample_fielders,
    get_keeper,
    MatchFormat as ServiceMatchFormat,
    FieldPlacement as ServicePlacement,
    FielderProfile,
    get_phase_from_over
)
from backend.app.services.optimizer import recommend_field
from backend.app.services.simulator import generate_candidate_fields
from backend.app.services.rules_engine import validate_field
from backend.app.services.metrics import compute_ers, compute_ewo, compute_cds
from backend.app.services.ml_prediction_engine import compute_ml_matchup_prediction
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
    DATA_DIR
)

# Cache deliveries dataset on module load
try:
    deliveries_df = pd.read_csv(DATA_DIR / 'real_batters_deliveries.csv')
    AVAILABLE_REAL_BATTERS = get_available_batters_from_df(deliveries_df)
except Exception:
    deliveries_df = None
    AVAILABLE_REAL_BATTERS = []

router = APIRouter(prefix="/api/v1", tags=["analysis"])


@router.get("/players", status_code=status.HTTP_200_OK)
def get_players_list():
    sample_bowlers = [b.name for b in get_sample_bowlers()]
    batters_list = AVAILABLE_REAL_BATTERS if AVAILABLE_REAL_BATTERS else [b.name for b in get_sample_batters()]
    return {
        "batters": batters_list,
        "bowlers": sample_bowlers
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
    status_code=status.HTTP_202_ACCEPTED,
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

    # Resolve batter profile (dynamic from CSV dataset if present)
    batter = None
    if deliveries_df is not None and request.batter_name in AVAILABLE_REAL_BATTERS:
        try:
            real_profiles = load_all_batters_from_df(deliveries_df)
            batter = next((b for b in real_profiles if b.name.lower() == request.batter_name.lower()), None)
        except Exception:
            pass

    if batter is None:
        batters = get_sample_batters()
        batter = next((b for b in batters if b.name.lower() == request.batter_name.lower()), batters[0])

    bowlers = get_sample_bowlers()
    bowler = next((b for b in bowlers if b.name.lower() == request.bowler_name.lower()), bowlers[0])

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

    # Query head-to-head matchup statistics
    from backend.app.services.matchup_stats import get_matchup_stats
    h2h_stats = get_matchup_stats(request.batter_name, request.bowler_name)

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
        ground_preset_id=ground.id
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
        format_record=fmt_rec_schema
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

    return AnalysisResponse(
        status="available",
        data_driven=True if request.batter_name in AVAILABLE_REAL_BATTERS else False,
        reason="Deterministic expert recommendation rules engine with Bayesian ML simulation.",
        placements=placements_schema,
        ers=result.ers,
        ewo=result.ewo,
        cds=result.cds,
        tactical_explanations=result.tactical_explanations,
        is_legal=result.is_legal,
        violations=result.violations,
        matchup_stats=h2h_stats,
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
    batter = None
    if deliveries_df is not None and request.batter_name in AVAILABLE_REAL_BATTERS:
        try:
            real_profiles = load_all_batters_from_df(deliveries_df)
            batter = next((b for b in real_profiles if b.name.lower() == request.batter_name.lower()), None)
        except Exception:
            pass

    if batter is None:
        batters = get_sample_batters()
        batter = next((b for b in batters if b.name.lower() == request.batter_name.lower()), batters[0])

    bowlers = get_sample_bowlers()
    bowler = next((b for b in bowlers if b.name.lower() == request.bowler_name.lower()), bowlers[0])

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
        ground_preset_id=ground.id
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
        format_record=fmt_rec_schema
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

    return EvaluateFieldResponse(
        ers=round(ers, 2),
        ewo=round(ewo, 2),
        cds=round(cds, 2),
        is_legal=is_legal,
        violations=violations,
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