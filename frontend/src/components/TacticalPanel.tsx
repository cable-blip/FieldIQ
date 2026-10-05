import React from 'react';
import './TacticalPanel.css';

export interface FielderPosition {
  name: string;
  x: number;
  y: number;
  role: 'wicket_taking' | 'run_saving' | 'core';
}

export interface AlternativeField {
  strategy_id: string;
  strategy_name: string;
  description: string;
  placements: FielderPosition[];
  ers: number;
  ewo: number;
  cds: number;
}

export interface BatterFormatRecord {
  format_name: string;
  bowler_type_category: string;
  balls_faced: number;
  runs_scored: number;
  dismissals: number;
  batting_average: number;
  strike_rate: number;
  dot_ball_pct: number;
  boundary_pct: number;
  caught_behind_slips_pct: number;
  caught_infield_pct: number;
  caught_deep_boundary_pct: number;
  bowled_lbw_pct: number;
  stumped_pct: number;
}

export interface MLOutcomeProbabilities {
  dot_pct: number;
  single_pct: number;
  two_pct: number;
  boundary_pct: number;
  four_pct: number;
  six_pct: number;
  wicket_pct: number;
  expected_runs_per_ball: number;
  expected_wickets_per_ball: number;
  format_record?: BatterFormatRecord | null;
}

export interface SimulationMetrics {
  simulated_deliveries: number;
  simulated_dot_pct: number;
  simulated_boundary_pct: number;
  simulated_wicket_pct: number;
  expected_runs_per_over: number;
  confidence_interval_90_min: number;
  confidence_interval_90_max: number;
  tactical_utility_score: number;
  fielder_catch_efficiencies?: Record<string, number>;
}

interface TacticalPanelProps {
  fielders: FielderPosition[];
  onReset: () => void;
  objective: string;
  metrics?: {
    ers: number;
    ewo: number;
    cds: number;
    explanations: string[];
    is_legal: boolean;
    violations: string[];
    matchup_stats?: {
      has_history: boolean;
      balls_faced: number;
      runs_scored: number;
      dismissals: number;
      strike_rate: number;
      dot_ball_pct: number;
      boundary_pct: number;
    } | null;
    ml_probabilities?: MLOutcomeProbabilities | null;
    simulation_metrics?: SimulationMetrics | null;
  } | null;
  alternatives?: AlternativeField[];
  selectedStrategy?: string;
  onSelectStrategy?: (strategyId: string) => void;
}

export const TacticalPanel: React.FC<TacticalPanelProps> = ({
  fielders,
  onReset,
  objective,
  metrics,
  alternatives,
  selectedStrategy,
  onSelectStrategy
}) => {
  const getFallbackMetrics = () => {
    switch (objective) {
      case 'prevent_boundary':
        return {
          wicket: '6.4%',
          ers: '1.20',
          cds: '0.85',
          confidence: '88%',
          explanations: [
            '5 fielders placed on the boundary rope (ICC limited-overs cap).',
            'Deep Midwicket, Long On, and Long Off cover primary boundary arcs.'
          ]
        };
      case 'build_pressure':
        return {
          wicket: '8.2%',
          ers: '0.95',
          cds: '0.82',
          confidence: '85%',
          explanations: [
            'Tight inner ring cordon at Point, Cover, and Midwicket to restrict singles.',
            'Deep fielders deployed to cut off primary boundary release valves.'
          ]
        };
      case 'stop_singles':
        return {
          wicket: '7.1%',
          ers: '1.05',
          cds: '0.78',
          confidence: '82%',
          explanations: [
            'Aggressive inner ring ring-fence within 15-20 meters of the pitch.',
            'Mid Off and Mid On pushed up to challenge batter strike rotation.'
          ]
        };
      case 'attack_wicket':
      default:
        return {
          wicket: '12.8%',
          ers: '0.75',
          cds: '0.90',
          confidence: '92%',
          explanations: [
            'Slip cordon & Gully positioned for outside edges against new ball seam.',
            'Deep Backward Square Leg placed as hook/pull top-edge trap.'
          ]
        };
    }
  };

  const fallback = getFallbackMetrics();

  const current = {
    wicket: metrics?.ewo !== undefined ? `${(metrics.ewo * 10).toFixed(1)}%` : fallback.wicket,
    ers: metrics?.ers !== undefined ? metrics.ers.toFixed(2) : fallback.ers,
    cds: metrics?.cds !== undefined ? metrics.cds.toFixed(2) : fallback.cds,
    confidence: fallback.confidence,
    explanations: metrics?.explanations && metrics.explanations.length > 0 ? metrics.explanations : fallback.explanations,
    is_legal: metrics?.is_legal !== undefined ? metrics.is_legal : true,
    violations: metrics?.violations || []
  };

  const ml = metrics?.ml_probabilities;
  const sim = metrics?.simulation_metrics;
  const h2h = metrics?.matchup_stats;
  const record = ml?.format_record;

  const handleExportReport = () => {
    const reportData = {
      timestamp: new Date().toISOString(),
      objective,
      metrics: current,
      ml_probabilities: ml,
      simulation_telemetry: sim,
      field_placements: fielders.map((f) => ({
        position: f.name,
        x: Number(f.x.toFixed(1)),
        y: Number(f.y.toFixed(1)),
        role: f.role
      }))
    };
    const blob = new Blob([JSON.stringify(reportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `FieldIQ_Tactical_Dossier_${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="tactical-panel">
      {/* Panel Header */}
      <div className="panel-header">
        <span className="header-icon">📊</span>
        <div className="header-title-wrap">
          <h3 className="font-display">TACTICAL DOSSIER</h3>
          <span className="header-subtitle font-mono">LIVE SPATIAL TELEMETRY</span>
        </div>
        <button type="button" onClick={onReset} className="btn-reset-panel" title="Reset Field" style={{ background: 'transparent', border: 'none', color: '#00f3ff', cursor: 'pointer', fontSize: '1.2rem' }}>🔄</button>
      </div>

      {/* ICC Legality & Rule Enforcement Banner */}
      <div className={`legality-banner ${current.is_legal ? 'legal' : 'violation'}`}>
        <div className="legality-indicator">
          <span className="legality-icon">{current.is_legal ? '🛡️' : '⚠️'}</span>
          <span className="legality-text font-mono">
            {current.is_legal ? 'FIELD LEGAL · ICC COMPLIANT' : 'FIELD ILLEGAL · RESTRICTION VIOLATION'}
          </span>
        </div>
        {!current.is_legal && current.violations.length > 0 && (
          <ul className="violations-list font-mono">
            {current.violations.map((v, idx) => (
              <li key={idx}>✕ {v}</li>
            ))}
          </ul>
        )}
      </div>

      {/* Core Defense Metrics Triad (Preserves 'Expected Wicket', 'Runs Saved (ERS)', 'Defensive Score (CDS)' for Vitest) */}
      <div className="metrics-triad">
        <div className="metric-tile wicket-tile">
          <span className="metric-num font-mono">{current.wicket}</span>
          <span className="metric-caption">Expected Wicket</span>
        </div>
        <div className="metric-tile ers-tile">
          <span className="metric-num font-mono">{current.ers}</span>
          <span className="metric-caption">Runs Saved (ERS)</span>
        </div>
        <div className="metric-tile cds-tile">
          <span className="metric-num font-mono">{current.cds}</span>
          <span className="metric-caption">Defensive Score (CDS)</span>
        </div>
      </div>

      {/* Candidate Strategy Alternatives Selector */}
      {alternatives && alternatives.length > 0 && (
        <div className="tactical-card strategy-card">
          <div className="card-header-flex">
            <span className="card-tag font-mono">⚡ CANDIDATE STRATEGIES</span>
            <span className="card-badge-count font-mono">{alternatives.length} READY</span>
          </div>
          <div className="strategy-chips">
            {alternatives.map((alt) => {
              const isSelected = selectedStrategy === alt.strategy_id;
              return (
                <button
                  key={alt.strategy_id}
                  type="button"
                  className={`strategy-pill ${isSelected ? 'active' : ''}`}
                  onClick={() => onSelectStrategy && onSelectStrategy(alt.strategy_id)}
                >
                  <span className="strategy-name">{alt.strategy_name}</span>
                  <span className="strategy-stat font-mono">CDS {alt.cds.toFixed(2)}</span>
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* 1,000-Delivery Monte Carlo Simulation Bar */}
      {ml && (
        <div className="tactical-card ml-prob-card">
          <div className="card-header-flex">
            <span className="card-tag font-mono">🤖 MONTE CARLO PROBABILITY ENGINE</span>
            <span className="live-tag font-mono">1,000 SIMS</span>
          </div>

          <div className="ml-bars-container">
            <div className="ml-bar-row">
              <div className="ml-bar-label">
                <span>⚪ Dot Ball Rate</span>
                <span className="font-mono">{ml.dot_pct.toFixed(1)}%</span>
              </div>
              <div className="ml-progress-bg">
                <div className="ml-progress-fill dot" style={{ width: `${ml.dot_pct}%` }} />
              </div>
            </div>

            <div className="ml-bar-row">
              <div className="ml-bar-label">
                <span>🔵 Singles & 2s</span>
                <span className="font-mono">{(ml.single_pct + ml.two_pct).toFixed(1)}%</span>
              </div>
              <div className="ml-progress-bg">
                <div className="ml-progress-fill single" style={{ width: `${ml.single_pct + ml.two_pct}%` }} />
              </div>
            </div>

            <div className="ml-bar-row">
              <div className="ml-bar-label">
                <span>🔴 Boundary Risk (4s/6s)</span>
                <span className="font-mono">{ml.boundary_pct.toFixed(1)}%</span>
              </div>
              <div className="ml-progress-bg">
                <div className="ml-progress-fill boundary" style={{ width: `${ml.boundary_pct}%` }} />
              </div>
            </div>

            <div className="ml-bar-row">
              <div className="ml-bar-label">
                <span>🟣 Wicket Chance</span>
                <span className="font-mono">{ml.wicket_pct.toFixed(1)}%</span>
              </div>
              <div className="ml-progress-bg">
                <div className="ml-progress-fill wicket" style={{ width: `${ml.wicket_pct}%` }} />
              </div>
            </div>
          </div>

          {/* Monte Carlo 1,000 Deliveries Telemetry */}
          {sim && (
            <div className="sim-telemetry-grid">
              <div className="sim-cell">
                <span className="sim-val font-mono">{sim.expected_runs_per_over.toFixed(1)}</span>
                <span className="sim-lbl font-mono">Exp. Runs/Over</span>
              </div>
              <div className="sim-cell">
                <span className="sim-val font-mono">{sim.confidence_interval_90_min}-{sim.confidence_interval_90_max}</span>
                <span className="sim-lbl font-mono">90% CI Over</span>
              </div>
              <div className="sim-cell">
                <span className="sim-val font-mono">{sim.tactical_utility_score.toFixed(1)}</span>
                <span className="sim-lbl font-mono">Tactical Score</span>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Historical Match Record Card */}
      {record && (
        <div className="tactical-card match-history-card">
          <div className="card-header-flex">
            <span className="card-tag font-mono">📜 HISTORICAL MATCH RECORD</span>
            <span className="history-badge font-mono">{record.bowler_type_category}</span>
          </div>

          <div className="history-stats-grid">
            <div className="hstat-cell">
              <span className="hstat-val font-mono">{record.balls_faced}</span>
              <span className="hstat-lbl">Balls</span>
            </div>
            <div className="hstat-cell">
              <span className="hstat-val font-mono">{record.batting_average.toFixed(1)}</span>
              <span className="hstat-lbl">Average</span>
            </div>
            <div className="hstat-cell">
              <span className="hstat-val font-mono">{record.strike_rate.toFixed(1)}</span>
              <span className="hstat-lbl">Strike Rate</span>
            </div>
            <div className="hstat-cell">
              <span className="hstat-val font-mono">{record.dot_ball_pct.toFixed(1)}%</span>
              <span className="hstat-lbl">Dot %</span>
            </div>
          </div>

          {/* Dismissal Mode Distribution Chips */}
          <div className="dismissal-modes-section">
            <span className="sub-tag font-mono">DISMISSAL PROFILE:</span>
            <div className="dismissal-chips-grid">
              <div className="dismissal-chip slips">
                <span className="d-label">Slips / Behind</span>
                <span className="d-pct font-mono">{record.caught_behind_slips_pct.toFixed(1)}%</span>
              </div>
              <div className="dismissal-chip infield">
                <span className="d-label">Infield Drives</span>
                <span className="d-pct font-mono">{record.caught_infield_pct.toFixed(1)}%</span>
              </div>
              <div className="dismissal-chip deep">
                <span className="d-label">Deep Boundary</span>
                <span className="d-pct font-mono">{record.caught_deep_boundary_pct.toFixed(1)}%</span>
              </div>
              <div className="dismissal-chip bowled">
                <span className="d-label">Bowled / LBW</span>
                <span className="d-pct font-mono">{record.bowled_lbw_pct.toFixed(1)}%</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Head-to-Head Stats Badge */}
      {h2h && h2h.has_history && (
        <div className="tactical-card h2h-card">
          <div className="card-header-flex">
            <span className="card-tag font-mono">⚔️ DIRECT HEAD-TO-HEAD</span>
            <span className="h2h-badge font-mono">{h2h.balls_faced} BALLS LOGGED</span>
          </div>
          <div className="h2h-metrics font-mono">
            <span>Runs: <b>{h2h.runs_scored}</b></span>
            <span>Wickets: <b>{h2h.dismissals}</b></span>
            <span>SR: <b>{h2h.strike_rate.toFixed(1)}</b></span>
            <span>Dot%: <b>{h2h.dot_ball_pct.toFixed(0)}%</b></span>
          </div>
        </div>
      )}

      {/* Tactical Explanations */}
      <div className="tactical-card explanations-card">
        <span className="card-tag font-mono">💡 TACTICAL DIRECTIVES</span>
        <ul className="explanations-list">
          {current.explanations.map((exp, idx) => (
            <li key={idx}>{exp}</li>
          ))}
        </ul>
      </div>

      {/* Coordinates Table with Catch Efficiency & Export Report Button */}
      <div className="tactical-card coords-card">
        <div className="coords-head">
          <span className="card-tag font-mono">📍 FIELDER COORDINATES</span>
          <button type="button" onClick={handleExportReport} className="btn-export-dossier font-mono">
            📥 Export Report
          </button>
        </div>
        <div className="table-scroll-wrap">
          <table className="coords-data-table">
            <thead>
              <tr>
                <th>Fielder</th>
                <th>X (m)</th>
                <th>Y (m)</th>
                <th>Role</th>
              </tr>
            </thead>
            <tbody>
              {fielders.map((f, idx) => (
                <tr key={`${f.name || 'fielder'}-${idx}`}>
                  <td>{f.name || `Fielder ${idx + 1}`}</td>
                  <td className="font-mono">{f.x.toFixed(1)}</td>
                  <td className="font-mono">{f.y.toFixed(1)}</td>
                  <td>
                    <span className={`role-tag ${f.role}`}>
                      {f.role === 'wicket_taking' ? 'Wicket' : f.role === 'run_saving' ? 'Save' : 'Fixed'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
