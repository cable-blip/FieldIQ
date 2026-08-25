import React from 'react';
import './TacticalPanel.css';

export interface FielderPosition {
  name: string;
  x: number;
  y: number;
  role: 'wicket_taking' | 'run_saving' | 'core';
}

interface TacticalPanelProps {
  fielders: FielderPosition[];
  onReset: () => void;
  objective: string;
}

export const TacticalPanel: React.FC<TacticalPanelProps> = ({ fielders, onReset, objective }) => {
  // Mocked/synthetic values aligned with tactical objectives
  const getMetrics = () => {
    switch (objective) {
      case 'prevent_boundary':
        return { wicket: '6.4%', boundary: '3.1%', runs: '3.21', confidence: '88%' };
      case 'build_pressure':
        return { wicket: '10.2%', boundary: '5.8%', runs: '4.10', confidence: '82%' };
      case 'stop_singles':
        return { wicket: '8.1%', boundary: '9.4%', runs: '3.80', confidence: '80%' };
      case 'attack_wicket':
      default:
        return { wicket: '18.7%', boundary: '11.2%', runs: '0.91', confidence: '85%' };
    }
  };

  const metrics = getMetrics();

  return (
    <div className="tactical-panel">
      <h3>Tactical Intelligence</h3>
      
      {/* Metrics Section */}
      <div className="metrics-grid">
        <div className="metric-box">
          <span className="metric-val">{metrics.wicket}</span>
          <span className="metric-label">Expected Wicket</span>
        </div>
        <div className="metric-box">
          <span className="metric-val">{metrics.boundary}</span>
          <span className="metric-label">Expected Boundary</span>
        </div>
        <div className="metric-box">
          <span className="metric-val">{metrics.runs}</span>
          <span className="metric-label">Expected Runs / Ball</span>
        </div>
      </div>

      <div className="confidence-section">
        <div className="confidence-header">
          <span>Recommendation Confidence</span>
          <span>{metrics.confidence}</span>
        </div>
        <div className="confidence-bar-bg">
          <div className="confidence-bar-fill" style={{ width: metrics.confidence }} />
        </div>
      </div>

      {/* Explanation Box */}
      <div className="explanation-box">
        <h4>Why this field?</h4>
        <ul>
          {objective === 'attack_wicket' ? (
            <>
              <li>1st Slip and Gully are reserved to capture outside edges.</li>
              <li>Silly Mid Off captures close drives.</li>
              <li>Inner circle fielders are placed at saving zones to build pressure.</li>
            </>
          ) : objective === 'prevent_boundary' ? (
            <>
              <li>5 fielders are placed on the boundary rope (ODI / T20 maximum cap).</li>
              <li>Deep Midwicket, Long On, and Long Off cover straight boundaries.</li>
              <li>No close-catching fielders are reserved.</li>
            </>
          ) : (
            <>
              <li>Balanced field layout focusing on minimizing run rates.</li>
              <li>Fielder capabilities matched to expected shot densities.</li>
            </>
          )}
        </ul>
      </div>

      {/* Coordinates Table */}
      <div className="coordinates-section">
        <div className="coordinates-header">
          <h4>Fielder Coordinates</h4>
          <button type="button" onClick={onReset} className="btn btn-reset">
            🔄 Reset Positions
          </button>
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
