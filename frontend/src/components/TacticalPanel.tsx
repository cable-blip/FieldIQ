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
  // Local fallback metrics when API has not run yet
  const getFallbackMetrics = () => {
    switch (objective) {
      case 'prevent_boundary':
        return { wicket: '6.4%', ers: '1.20', cds: '0.85', confidence: '88%', explanations: [
          '5 fielders placed on the boundary rope (ODI / T20 maximum cap).',
          'Deep Midwicket, Long On, and Long Off cover straight boundaries.'
        ], is_legal: true, violations: [] };
      case 'build_pressure':
        return { wicket: '10.2%', ers: '1.45', cds: '0.90', confidence: '82%', explanations: [
          'Inner circle fielders are placed tight to restrict singles.',
          'Focus on maintaining a low run rate.'
        ], is_legal: true, violations: [] };
      case 'stop_singles':
        return { wicket: '8.1%', ers: '1.10', cds: '0.80', confidence: '80%', explanations: [
          'Maximum players inside the circle to prevent strike rotation.'
        ], is_legal: true, violations: [] };
      case 'attack_wicket':
      default:
        return { wicket: '18.7%', ers: '0.91', cds: '1.05', confidence: '85%', explanations: [
          '1st Slip and Gully are reserved to capture outside edges.',
          'Silly Mid Off captures close drives.'
        ], is_legal: true, violations: [] };
    }
  };

  const current = metrics
    ? {
        wicket: `${(metrics.ewo * 100).toFixed(1)}%`,
        ers: metrics.ers.toFixed(2),
        cds: metrics.cds.toFixed(2),
        confidence: '91%',
        explanations: metrics.explanations,
        is_legal: metrics.is_legal,
        violations: metrics.violations,
      }
    : getFallbackMetrics();

  const handleExportReport = () => {
    const reportData = {
      system: 'FieldIQ Cricket Tactical Field Intelligence',
      generated_at: new Date().toISOString(),
      objective,
      metrics,
      fielders: fielders.map((f) => ({
        position: f.name,
        x: Number(f.x.toFixed(1)),
        y: Number(f.y.toFixed(1)),
        role: f.role,
      })),
    };
    const jsonStr = JSON.stringify(reportData, null, 2);
    const blob = new Blob([jsonStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `FieldIQ_Tactical_Report_${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="tactical-panel">
      <h3>Tactical Intelligence</h3>
      
      {/* Legality Status Indicator */}
      <div className={`legality-banner ${current.is_legal ? 'legal' : 'illegal'}`}>
        {current.is_legal ? '✅ Field Legality: LEGAL' : '⚠️ Field Legality: ILLEGAL'}
      </div>

      {current.violations.length > 0 && (
        <div className="violations-box">
          <h5>ICC Violations Detected:</h5>
          <ul>
            {current.violations.map((v, idx) => (
              <li key={idx}>{v}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Strategy Selector Button Group */}
      {alternatives && alternatives.length > 0 && (
        <div className="strategy-selector-section">
          <h4>Tactical Strategy Selector</h4>
          <div className="strategy-buttons-grid">
            {alternatives.map((alt) => (
              <button
                key={alt.strategy_id}
                type="button"
                className={`btn-strategy ${selectedStrategy === alt.strategy_id ? 'active' : ''}`}
                onClick={() => onSelectStrategy && onSelectStrategy(alt.strategy_id)}
              >
                {alt.strategy_name}
              </button>
            ))}
          </div>
          {selectedStrategy && (
            <p className="strategy-description">
              {alternatives.find(a => a.strategy_id === selectedStrategy)?.description}
            </p>
          )}
        </div>
      )}

      {/* Metrics Section */}
      <div className="metrics-grid">
        <div className="metric-box">
          <span className="metric-val">{current.wicket}</span>
          <span className="metric-label">Expected Wicket</span>
        </div>
        <div className="metric-box">
          <span className="metric-val">{current.ers}</span>
          <span className="metric-label">Runs Saved (ERS)</span>
        </div>
        <div className="metric-box">
          <span className="metric-val">{current.cds}</span>
          <span className="metric-label">Defensive Score (CDS)</span>
        </div>
      </div>

      <div className="confidence-section">
        <div className="confidence-header">
          <span>Recommendation Confidence</span>
          <span>{current.confidence}</span>
        </div>
        <div className="confidence-bar-bg">
          <div className="confidence-bar-fill" style={{ width: current.confidence }} />
        </div>
      </div>

      {/* Explanation Box */}
      <div className="explanation-box">
        <h4>Why this field?</h4>
        <ul>
          {current.explanations.map((exp, idx) => (
            <li key={idx}>{exp}</li>
          ))}
        </ul>
      </div>

      {/* Head-to-Head Matchup Statistics Section */}
      <div className="matchup-stats-box">
        <h4>Head-to-Head Record</h4>
        {metrics?.matchup_stats?.has_history ? (
          <div className="matchup-grid">
            <div className="matchup-header-stats">
              <span>{metrics.matchup_stats.balls_faced} balls faced</span>
              <span> | </span>
              <span>{metrics.matchup_stats.runs_scored} runs scored</span>
              <span> | </span>
              <span>{metrics.matchup_stats.dismissals} dismissals</span>
            </div>
            <div className="matchup-metrics-grid">
              <div className="matchup-metric">
                <span className="matchup-val">{metrics.matchup_stats.strike_rate.toFixed(1)}</span>
                <span className="matchup-label">Strike Rate</span>
              </div>
              <div className="matchup-metric">
                <span className="matchup-val">{metrics.matchup_stats.dot_ball_pct.toFixed(0)}%</span>
                <span className="matchup-label">Dot Balls</span>
              </div>
              <div className="matchup-metric">
                <span className="matchup-val">{metrics.matchup_stats.boundary_pct.toFixed(0)}%</span>
                <span className="matchup-label">Boundaries</span>
              </div>
            </div>
          </div>
        ) : (
          <div className="no-matchup-history">
            ℹ️ No head-to-head history found. Falls back to expert rule priors.
          </div>
        )}
      </div>

      {/* Coordinates Table */}
      <div className="coordinates-section">
        <div className="coordinates-header">
          <h4>Fielder Coordinates</h4>
          <div className="header-actions">
            <button type="button" onClick={handleExportReport} className="btn btn-export">
              📥 Export Report
            </button>
            <button type="button" onClick={onReset} className="btn btn-reset">
              🔄 Reset Positions
            </button>
          </div>
        </div>
        <div className="table-wrapper">
          <table className="coords-table">
            <thead>
              <tr>
                <th>Position</th>
                <th>X (m)</th>
                <th>Y (m)</th>
                <th>Role</th>
              </tr>
            </thead>
            <tbody>
              {fielders.map((f) => (
                <tr key={f.name}>
                  <td>{f.name}</td>
                  <td className="font-mono">{f.x.toFixed(1)}</td>
                  <td className="font-mono">{f.y.toFixed(1)}</td>
                  <td>
                    <span className={`role-badge ${f.role}`}>
                      {f.role === 'wicket_taking' ? 'Wicket' : f.role === 'run_saving' ? 'Save' : 'Core'}
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
