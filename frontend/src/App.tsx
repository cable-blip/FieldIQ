import { useState } from 'react';
import { Navbar } from './components/Navbar';
import { MatchContextPanel } from './components/MatchContextPanel';
import type { MatchState } from './components/MatchContextPanel';
import { TacticalPanel } from './components/TacticalPanel';
import type { FielderPosition, AlternativeField } from './components/TacticalPanel';
import { ThreeField } from './components/ThreeField';
import { GameplanTimeline } from './components/GameplanTimeline';
import type { GameplanOverItem } from './components/GameplanTimeline';
import { DatasetStudioModal } from './components/DatasetStudioModal';
import './App.css';

const DEFAULT_FIELDERS: FielderPosition[] = [
  { name: 'Wicketkeeper', x: 0, y: -15, role: 'core' },
  { name: 'Bowler', x: 0, y: 15, role: 'core' },
  { name: '1st Slip', x: 3.5, y: -14, role: 'wicket_taking' },
  { name: '2nd Slip', x: 5.2, y: -13.2, role: 'wicket_taking' },
  { name: 'Gully', x: 7.5, y: -11.5, role: 'wicket_taking' },
  { name: 'Point', x: 22.0, y: -2.0, role: 'run_saving' },
  { name: 'Cover', x: 18.0, y: 10.0, role: 'run_saving' },
  { name: 'Mid Off', x: 8.0, y: 24.0, role: 'run_saving' },
  { name: 'Mid On', x: -8.0, y: 24.0, role: 'run_saving' },
  { name: 'Midwicket', x: -18.0, y: 10.0, role: 'run_saving' },
  { name: 'Square Leg', x: -22.0, y: -2.0, role: 'run_saving' },
];

function App() {
  const [fielders, setFielders] = useState<FielderPosition[]>(DEFAULT_FIELDERS);
  const [objective, setObjective] = useState<string>('attack_wicket');
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [metrics, setMetrics] = useState<any>(null);
  const [alternatives, setAlternatives] = useState<AlternativeField[]>([]);
  const [selectedStrategy, setSelectedStrategy] = useState<string>('balanced');
  const [zoneChart, setZoneChart] = useState<Record<string, number>>({});
  const [lastMatchState, setLastMatchState] = useState<MatchState | null>(null);
  const [isDatasetStudioOpen, setIsDatasetStudioOpen] = useState<boolean>(false);

  // Modern Venue & Environmental Aerodynamics State
  const [venueId, setVenueId] = useState<string>('lords');
  const [pitchType, setPitchType] = useState<string>('green_seam');
  const [windSpeed, setWindSpeed] = useState<number>(18);
  const [windAngle, setWindAngle] = useState<number>(45);

  // Multi-Over Strategic Gameplan State
  const [gameplanSequence, setGameplanSequence] = useState<GameplanOverItem[]>([]);
  const [activeOverIndex, setActiveOverIndex] = useState<number>(0);
  const [isGameplanActive, setIsGameplanActive] = useState<boolean>(false);

  // Live evaluation endpoint trigger for manual sphere drags
  const handleEvaluateCustomLayout = async (updatedFielders: FielderPosition[]) => {
    if (!lastMatchState) return;

    const evalPayload = {
      batter_name: lastMatchState.batter_name,
      bowler_name: lastMatchState.bowler_name,
      match_format: lastMatchState.match_format,
      over: lastMatchState.over,
      ground_preset_id: venueId,
      environmental_conditions: lastMatchState.environmental_conditions,
      placements: updatedFielders.map((f) => ({
        position_name: f.name || 'Fielder',
        fielder: {
          name: f.name || 'Fielder',
          jump: 0.8,
          catching: 0.8,
          arm: 0.8,
          close_in_skill: 0.8,
          boundary_skill: 0.8,
          preferred_positions: [],
        },
        x: f.x,
        y: f.y,
        role: f.role === 'core' ? 'wicket_taking' : f.role,
        reason: 'Custom user position',
      })),
    };

    try {
      const res = await fetch('/api/v1/analysis/evaluate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(evalPayload),
      });

      if (res.ok) {
        const evalData = await res.json();
        setMetrics((prev: any) => ({
          ...prev,
          ers: evalData.ers,
          ewo: evalData.ewo,
          cds: evalData.cds,
          is_legal: evalData.is_legal,
          violations: evalData.violations,
          ml_probabilities: evalData.ml_probabilities || prev?.ml_probabilities,
          simulation_metrics: evalData.simulation_metrics || prev?.simulation_metrics,
        }));
      }
    } catch {
      // Ignore transient network errors during drag
    }
  };

  // Drag handler updating positions in real-time
  const handleUpdateFielder = (name: string, x: number, y: number) => {
    const updated = fielders.map((f) => (f.name === name ? { ...f, x, y } : f));
    setFielders(updated);
    handleEvaluateCustomLayout(updated);
  };

  const handleResetPositions = () => {
    setFielders(DEFAULT_FIELDERS);
    setMetrics(null);
    setAlternatives([]);
    setSelectedStrategy('balanced');
    setZoneChart({});
    setLastMatchState(null);
    setGameplanSequence([]);
    setIsGameplanActive(false);
  };

  const handleCopyCoordinates = () => {
    const jsonStr = JSON.stringify(
      fielders.map((f) => ({
        position: f.name,
        x: Number(f.x.toFixed(1)),
        y: Number(f.y.toFixed(1)),
        role: f.role,
      })),
      null,
      2
    );
    navigator.clipboard.writeText(jsonStr);
  };

  const handleSelectStrategy = (strategyId: string) => {
    setSelectedStrategy(strategyId);
    const target = alternatives.find((a) => a.strategy_id === strategyId);
    if (target) {
      if (target.placements && target.placements.length > 0) {
        const mappedFielders = target.placements.map((p: any) => ({
          name: p.position_name || p.name || 'Fielder',
          x: p.x,
          y: p.y,
          role: p.role,
        }));
        setFielders(mappedFielders);
        handleEvaluateCustomLayout(mappedFielders);
      }
      setMetrics((prev: any) => ({
        ...prev,
        ers: target.ers,
        ewo: target.ewo,
        cds: target.cds,
      }));
    }
  };

  // Step between overs in the multi-over gameplan sequence
  const handleSelectGameplanOver = (overIdx: number) => {
    if (!gameplanSequence || !gameplanSequence[overIdx]) return;
    setActiveOverIndex(overIdx);

    const overPlan = gameplanSequence[overIdx];
    if (overPlan.placements && overPlan.placements.length > 0) {
      const mapped = overPlan.placements.map((p: any) => ({
        name: p.position_name || p.name || 'Fielder',
        x: p.x,
        y: p.y,
        role: p.role,
      }));
      setFielders(mapped);
    }

    setMetrics((prev: any) => ({
      ...prev,
      ers: overPlan.ers,
      ewo: overPlan.ewo,
      cds: overPlan.cds,
      is_legal: overPlan.is_legal,
      explanations: [overPlan.tactical_directive],
      ml_probabilities: overPlan.outcome_probabilities || prev?.ml_probabilities,
      simulation_metrics: overPlan.simulation_telemetry || prev?.simulation_metrics,
    }));
  };

  const handleMatchSubmit = async (matchState: MatchState) => {
    setLoading(true);
    setError(null);
    setObjective(matchState.tactical_objective);
    setLastMatchState(matchState);

    if (matchState.ground_preset_id) setVenueId(matchState.ground_preset_id);
    if (matchState.environmental_conditions?.pitch_type) {
      setPitchType(matchState.environmental_conditions.pitch_type);
    }
    if (matchState.environmental_conditions?.wind_speed_kph !== undefined) {
      setWindSpeed(matchState.environmental_conditions.wind_speed_kph);
    }
    if (matchState.environmental_conditions?.wind_angle_degrees !== undefined) {
      setWindAngle(matchState.environmental_conditions.wind_angle_degrees);
    }

    try {
      if (matchState.is_gameplan_mode) {
        // Multi-Over Strategic Gameplan Endpoint
        const gameplanPayload = {
          batter_name: matchState.batter_name,
          bowler_name: matchState.bowler_name,
          match_format: matchState.match_format,
          current_over: matchState.over,
          runs: matchState.runs,
          wickets: matchState.wickets,
          planned_overs: matchState.planned_overs || 4,
          tactical_objective: matchState.tactical_objective,
          ground_preset_id: matchState.ground_preset_id || venueId,
          environmental_conditions: matchState.environmental_conditions,
        };

        const response = await fetch('/api/v1/analysis/gameplan', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(gameplanPayload),
        });

        if (!response.ok) {
          throw new Error(`Gameplan engine returned HTTP ${response.status}`);
        }

        const gpData = await response.json();
        if (gpData.gameplan_sequence && gpData.gameplan_sequence.length > 0) {
          setGameplanSequence(gpData.gameplan_sequence);
          setIsGameplanActive(true);
          setActiveOverIndex(0);

          const firstOver = gpData.gameplan_sequence[0];
          if (firstOver.placements && firstOver.placements.length > 0) {
            const mapped = firstOver.placements.map((p: any) => ({
              name: p.position_name || p.name || 'Fielder',
              x: p.x,
              y: p.y,
              role: p.role,
            }));
            setFielders(mapped);
          }

          setMetrics({
            ers: firstOver.ers,
            ewo: firstOver.ewo,
            cds: firstOver.cds,
            explanations: [firstOver.tactical_directive],
            is_legal: firstOver.is_legal,
            violations: [],
            ml_probabilities: firstOver.outcome_probabilities,
            simulation_metrics: firstOver.simulation_telemetry,
          });
        }
      } else {
        // Standard Single-Over Optimization
        setIsGameplanActive(false);
        setGameplanSequence([]);

        const response = await fetch('/api/v1/analysis', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(matchState),
        });

        if (!response.ok) {
          throw new Error(`Server returned HTTP ${response.status}`);
        }

        const data = await response.json();
        
        if (data.placements && data.placements.length > 0) {
          const mappedFielders = data.placements.map((p: any) => ({
            name: p.position_name || p.name || 'Fielder',
            x: p.x,
            y: p.y,
            role: p.role,
          }));
          setFielders(mappedFielders);
        }

        if (data.zone_chart) {
          setZoneChart(data.zone_chart);
        }

        setMetrics({
          ers: data.ers,
          ewo: data.ewo,
          cds: data.cds,
          explanations: data.tactical_explanations,
          is_legal: data.is_legal,
          violations: data.violations,
          matchup_stats: data.matchup_stats,
          ml_probabilities: data.ml_probabilities,
          simulation_metrics: data.simulation_metrics,
        });

        if (data.alternative_fields && data.alternative_fields.length > 0) {
          const mappedAlts: AlternativeField[] = data.alternative_fields.map((alt: any) => ({
            strategy_id: alt.strategy_id,
            strategy_name: alt.strategy_name,
            description: alt.description,
            placements: alt.placements.map((p: any) => ({
              name: p.position_name || p.name || 'Fielder',
              x: p.x,
              y: p.y,
              role: p.role,
            })),
            ers: alt.ers,
            ewo: alt.ewo,
            cds: alt.cds,
          }));
          setAlternatives(mappedAlts);
          setSelectedStrategy('balanced');
        }
      }

    } catch (err: any) {
      setError(err.message || 'Failed to fetch tactical analysis.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-layout">
      {/* Top Cybernetic Command Navbar */}
      <Navbar
        onOpenDatasetStudio={() => setIsDatasetStudioOpen(true)}
        onResetLayout={handleResetPositions}
        onCopyCoordinates={handleCopyCoordinates}
        venueName={venueId}
        isGameplanActive={isGameplanActive}
      />

      {error && (
        <div className="app-error-banner font-mono">
          ⚠️ <strong>API Connection Error:</strong> {error} (Displaying local fallback metrics)
        </div>
      )}

      <main className="app-main">
        <div className="app-grid-layout">
          {/* Left Column: Match Context & Environmental Aerodynamics */}
          <aside className="sidebar-left">
            <MatchContextPanel
              onSubmit={handleMatchSubmit}
              loading={loading}
              onVenueChange={(vId) => setVenueId(vId)}
              onPitchTypeChange={(pType) => setPitchType(pType)}
            />
          </aside>

          {/* Center Column: 3D Spatial Arena & Gameplan Timeline */}
          <section className="center-viewport">
            <ThreeField
              fielders={fielders}
              onUpdateFielder={handleUpdateFielder}
              zoneChart={zoneChart}
              venueId={venueId}
              pitchType={pitchType}
              windSpeedKph={windSpeed}
              windAngleDegrees={windAngle}
            />

            {/* Strategic Gameplan Timeline Sequencer */}
            {isGameplanActive && gameplanSequence.length > 0 && (
              <GameplanTimeline
                sequence={gameplanSequence}
                activeOverIndex={activeOverIndex}
                onSelectOver={handleSelectGameplanOver}
                groundName={venueId}
                pitchType={pitchType}
              />
            )}
          </section>

          {/* Right Column: Tactical Dossier & Telemetry */}
          <aside className="sidebar-right">
            <TacticalPanel
              fielders={fielders}
              onReset={handleResetPositions}
              objective={objective}
              metrics={metrics}
              alternatives={alternatives}
              selectedStrategy={selectedStrategy}
              onSelectStrategy={handleSelectStrategy}
            />
          </aside>
        </div>
      </main>

      {/* Dataset Studio Modal */}
      <DatasetStudioModal
        isOpen={isDatasetStudioOpen}
        onClose={() => setIsDatasetStudioOpen(false)}
      />
    </div>
  );
}

export default App;
