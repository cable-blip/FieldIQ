import React, { useState, useEffect } from 'react';

interface AnalysisResponse {
  analysis_id: string;
  status: string;
  is_legal: boolean;
  violations: string[];
  data_coverage: string;
  placements: Array<{
    position_name: string;
    x: number;
    y: number;
    role: string;
    reason: string;
    fielder: {
      name: string;
    };
  }>;
  matchup_stats: {
    has_history: boolean;
    balls_faced: number;
    runs_scored: number;
    dismissals: number;
    strike_rate: number | null;
    dot_ball_pct: number | null;
    boundary_pct: number | null;
    source: string;
    data_coverage_note: string;
  };
  model_confidence?: {
    wicket_prediction_recall: number;
    wicket_prediction_precision: number;
    status: string;
  };
  ml_probabilities?: {
    dot_pct: number;
    single_pct: number;
    two_pct: number;
    boundary_pct: number;
    four_pct: number;
    six_pct: number;
    wicket_pct: number;
    expected_runs_per_ball: number;
  };
  bowler_provenance?: {
    bowler_type: string;
    new_ball_strength: string;
    death_bowling_strength: string;
  };
}

export const MinimalFormView: React.FC = () => {
  // Form State
  const [batters, setBatters] = useState<string[]>([]);
  const [bowlers, setBowlers] = useState<string[]>([]);
  const [tacticalObjectives, setTacticalObjectives] = useState<string[]>([]);
  const [matchFormats, setMatchFormats] = useState<string[]>([]);

  const [selectedBatter, setSelectedBatter] = useState<string>('Virat Kohli');
  const [selectedBowler, setSelectedBowler] = useState<string>('Mohammad Asif');
  const [selectedFormat, setSelectedFormat] = useState<string>('T20');
  const [selectedOver, setSelectedOver] = useState<number>(3);
  const [runs, setRuns] = useState<number>(28);
  const [wickets, setWickets] = useState<number>(0);
  const [selectedObjective, setSelectedObjective] = useState<string>('attack_wicket');

  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AnalysisResponse | null>(null);

  // 1. Fetch available options on mount
  useEffect(() => {
    const fetchOptions = async () => {
      try {
        const res = await fetch('/api/v1/players');
        if (!res.ok) throw new Error(`HTTP error ${res.status}`);
        const data = await res.json();

        if (data.batters && data.batters.length > 0) {
          setBatters(data.batters);
          if (!data.batters.includes(selectedBatter)) {
            setSelectedBatter(data.batters[0]);
          }
        }
        if (data.bowlers && data.bowlers.length > 0) {
          setBowlers(data.bowlers);
        }
        if (data.tactical_objectives && data.tactical_objectives.length > 0) {
          setTacticalObjectives(data.tactical_objectives);
        } else {
          setTacticalObjectives(['attack_wicket', 'prevent_boundary', 'build_pressure', 'stop_singles']);
        }
        if (data.match_formats && data.match_formats.length > 0) {
          setMatchFormats(data.match_formats);
        } else {
          setMatchFormats(['T20', 'ODI']);
        }
      } catch (err: any) {
        setError(`Failed to load player options: ${err.message}`);
      }
    };
    fetchOptions();
  }, []);

  // 2. Submit analysis request
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    const payload = {
      batter_name: selectedBatter,
      bowler_name: selectedBowler,
      match_format: selectedFormat,
      innings: 1,
      over: Number(selectedOver),
      runs: Number(runs),
      wickets: Number(wickets),
      tactical_objective: selectedObjective,
    };

    try {
      const res = await fetch('/api/v1/analysis', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errorBody = await res.text();
        throw new Error(`API Error ${res.status}: ${errorBody}`);
      }

      const data: AnalysisResponse = await res.json();
      setResult(data);
    } catch (err: any) {
      setError(err.message || 'Analysis request failed');
    } finally {
      setLoading(false);
    }
  };

  const maxOvers = selectedFormat === 'T20' ? 20 : 50;
  const overOptions = Array.from({ length: maxOvers }, (_, i) => i + 1);

  const getPhaseName = (overNum: number) => {
    if (selectedFormat === 'T20') {
      if (overNum <= 6) return 'Powerplay';
      if (overNum <= 15) return 'Middle';
      return 'Death';
    } else {
      if (overNum <= 10) return 'Powerplay';
      if (overNum <= 40) return 'Middle';
      return 'Death';
    }
  };

  return (
    <div style={{ maxWidth: '1100px', margin: '0 auto', padding: '24px', fontFamily: 'system-ui, -apple-system, sans-serif', color: '#1a1a1a' }}>
      <header style={{ borderBottom: '2px solid #222', paddingBottom: '12px', marginBottom: '24px' }}>
        <h1 style={{ margin: '0 0 6px 0', fontSize: '24px' }}>FieldIQ Tactical Intelligence — Phase 5A Minimal Client</h1>
        <p style={{ margin: 0, color: '#555', fontSize: '14px' }}>
          Deterministic cricket rules, data-driven matchup intelligence, and explicit uncertainty disclosure. (No 3D / No Canvas).
        </p>
      </header>

      {error && (
        <div style={{ backgroundColor: '#ffebe8', border: '1px solid #cc0000', color: '#990000', padding: '12px', marginBottom: '20px', borderRadius: '4px' }}>
          <strong>Error:</strong> {error}
        </div>
      )}

      {/* Form Section */}
      <form onSubmit={handleSubmit} style={{ backgroundColor: '#f8f9fa', border: '1px solid #ddd', padding: '20px', borderRadius: '6px', marginBottom: '28px' }}>
        <h2 style={{ fontSize: '18px', marginTop: 0, marginBottom: '16px' }}>Input Match Situation</h2>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px', marginBottom: '16px' }}>
          {/* Batter Selection */}
          <div>
            <label htmlFor="batter-select" style={{ display: 'block', fontWeight: 'bold', marginBottom: '6px', fontSize: '13px' }}>
              Batter (Confirmed Dataset):
            </label>
            <select
              id="batter-select"
              value={selectedBatter}
              onChange={(e) => setSelectedBatter(e.target.value)}
              style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ccc' }}
            >
              {batters.map((b) => (
                <option key={b} value={b}>{b}</option>
              ))}
            </select>
          </div>

          {/* Bowler Selection with Native Datalist */}
          <div>
            <label htmlFor="bowler-input" style={{ display: 'block', fontWeight: 'bold', marginBottom: '6px', fontSize: '13px' }}>
              Bowler ({bowlers.length} available):
            </label>
            <input
              id="bowler-input"
              list="bowler-options"
              value={selectedBowler}
              onChange={(e) => setSelectedBowler(e.target.value)}
              placeholder="Search or enter bowler..."
              style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ccc', boxSizing: 'border-box' }}
            />
            <datalist id="bowler-options">
              {bowlers.map((bw) => (
                <option key={bw} value={bw} />
              ))}
            </datalist>
          </div>

          {/* Match Format */}
          <div>
            <label htmlFor="format-select" style={{ display: 'block', fontWeight: 'bold', marginBottom: '6px', fontSize: '13px' }}>
              Format:
            </label>
            <select
              id="format-select"
              value={selectedFormat}
              onChange={(e) => setSelectedFormat(e.target.value)}
              style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ccc' }}
            >
              {matchFormats.map((fmt) => (
                <option key={fmt} value={fmt}>{fmt}</option>
              ))}
            </select>
          </div>

          {/* Over Selection (1-Indexed) */}
          <div>
            <label htmlFor="over-select" style={{ display: 'block', fontWeight: 'bold', marginBottom: '6px', fontSize: '13px' }}>
              Over (1-indexed):
            </label>
            <select
              id="over-select"
              value={selectedOver}
              onChange={(e) => setSelectedOver(Number(e.target.value))}
              style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ccc' }}
            >
              {overOptions.map((o) => (
                <option key={o} value={o}>Over {o} ({getPhaseName(o)})</option>
              ))}
            </select>
          </div>

          {/* Score Runs */}
          <div>
            <label htmlFor="runs-input" style={{ display: 'block', fontWeight: 'bold', marginBottom: '6px', fontSize: '13px' }}>
              Innings Runs:
            </label>
            <input
              id="runs-input"
              type="number"
              min="0"
              value={runs}
              onChange={(e) => setRuns(Number(e.target.value))}
              style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ccc', boxSizing: 'border-box' }}
            />
          </div>

          {/* Score Wickets */}
          <div>
            <label htmlFor="wickets-select" style={{ display: 'block', fontWeight: 'bold', marginBottom: '6px', fontSize: '13px' }}>
              Wickets Down (0–9):
            </label>
            <select
              id="wickets-select"
              value={wickets}
              onChange={(e) => setWickets(Number(e.target.value))}
              style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ccc' }}
            >
              {[0, 1, 2, 3, 4, 5, 6, 7, 8, 9].map((w) => (
                <option key={w} value={w}>{w}</option>
              ))}
            </select>
          </div>

          {/* Tactical Objective */}
          <div>
            <label htmlFor="objective-select" style={{ display: 'block', fontWeight: 'bold', marginBottom: '6px', fontSize: '13px' }}>
              Tactical Objective:
            </label>
            <select
              id="objective-select"
              value={selectedObjective}
              onChange={(e) => setSelectedObjective(e.target.value)}
              style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ccc' }}
            >
              {tacticalObjectives.map((obj) => (
                <option key={obj} value={obj}>{obj}</option>
              ))}
            </select>
          </div>
        </div>

        <button
          id="submit-analysis-btn"
          type="submit"
          disabled={loading}
          style={{
            backgroundColor: '#0056b3',
            color: '#fff',
            border: 'none',
            padding: '10px 20px',
            borderRadius: '4px',
            fontWeight: 'bold',
            cursor: loading ? 'not-allowed' : 'pointer',
            fontSize: '14px',
          }}
        >
          {loading ? 'Evaluating Tactical Placements...' : 'Generate Field Recommendation'}
        </button>
      </form>

      {/* Results Display */}
      {result && (
        <div id="analysis-results-section" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {/* Legality & Status Banner */}
          <div
            id="legality-banner"
            style={{
              padding: '14px 18px',
              borderRadius: '6px',
              backgroundColor: result.is_legal ? '#e6f7ec' : '#ffebe8',
              border: `1px solid ${result.is_legal ? '#28a745' : '#dc3545'}`,
            }}
          >
            <h3 style={{ margin: '0 0 6px 0', fontSize: '16px', color: result.is_legal ? '#155724' : '#721c24' }}>
              Field Legality: {result.is_legal ? 'LEGAL (All ICC Constraints Satisfied)' : 'ILLEGAL FIELD'}
            </h3>
            {result.violations && result.violations.length > 0 ? (
              <ul style={{ margin: 0, paddingLeft: '20px', color: '#721c24' }}>
                {result.violations.map((v, i) => (
                  <li key={i}>{v}</li>
                ))}
              </ul>
            ) : (
              <span style={{ fontSize: '13px', color: '#155724' }}>
                11 fielders placed; legal Powerplay boundary/circle limits verified.
              </span>
            )}
          </div>

          {/* Cards Row: Matchup Data Coverage & Model Confidence Disclosure */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '16px' }}>
            {/* Matchup Intelligence Card */}
            <div id="data-coverage-card" style={{ border: '1px solid #ccc', borderRadius: '6px', padding: '16px', backgroundColor: '#fff' }}>
              <h3 style={{ margin: '0 0 10px 0', fontSize: '15px', borderBottom: '1px solid #eee', paddingBottom: '6px' }}>
                Data Coverage & Matchup Provenance
              </h3>
              <p style={{ margin: '4px 0', fontSize: '13px' }}>
                <strong>Tier:</strong> <span id="coverage-tier" style={{ padding: '2px 6px', backgroundColor: '#e9ecef', borderRadius: '3px' }}>{result.data_coverage}</span>
              </p>
              <p style={{ margin: '4px 0', fontSize: '13px' }}>
                <strong>Balls Faced:</strong> {result.matchup_stats.balls_faced}
              </p>
              <p style={{ margin: '4px 0', fontSize: '13px' }}>
                <strong>Strike Rate:</strong> {result.matchup_stats.strike_rate !== null ? result.matchup_stats.strike_rate : 'None (Insufficient history)'}
              </p>
              <p style={{ margin: '4px 0', fontSize: '13px' }}>
                <strong>Dot Ball %:</strong> {result.matchup_stats.dot_ball_pct !== null ? `${result.matchup_stats.dot_ball_pct}%` : 'None'}
              </p>
              <p style={{ margin: '8px 0 0 0', fontSize: '12px', color: '#555', fontStyle: 'italic' }}>
                {result.matchup_stats.data_coverage_note}
              </p>
            </div>

            {/* Model Confidence Disclosure Card */}
            <div id="model-confidence-card" style={{ border: '1px solid #ccc', borderRadius: '6px', padding: '16px', backgroundColor: '#fff' }}>
              <h3 style={{ margin: '0 0 10px 0', fontSize: '15px', borderBottom: '1px solid #eee', paddingBottom: '6px' }}>
                Model Confidence & Uncertainty
              </h3>
              {result.model_confidence ? (
                <>
                  <p style={{ margin: '4px 0', fontSize: '13px' }}>
                    <strong>Measured Wicket Recall:</strong> {(result.model_confidence.wicket_prediction_recall * 100).toFixed(1)}%
                  </p>
                  <p style={{ margin: '4px 0', fontSize: '13px' }}>
                    <strong>Measured Wicket Precision:</strong> {(result.model_confidence.wicket_prediction_precision * 100).toFixed(1)}%
                  </p>
                  <p style={{ margin: '4px 0', fontSize: '13px' }}>
                    <strong>Status:</strong> <span style={{ padding: '2px 6px', backgroundColor: '#fff3cd', color: '#856404', borderRadius: '3px' }}>{result.model_confidence.status}</span>
                  </p>
                </>
              ) : (
                <p style={{ fontSize: '13px', color: '#777' }}>Confidence metadata not attached</p>
              )}
              {result.ml_probabilities && (
                <p style={{ margin: '8px 0 0 0', fontSize: '13px' }}>
                  <strong>Evaluated P(Wicket):</strong> {(result.ml_probabilities.wicket_pct * 100).toFixed(2)}% |{' '}
                  <strong>Exp Runs/Ball:</strong> {result.ml_probabilities.expected_runs_per_ball.toFixed(2)}
                </p>
              )}
              {result.bowler_provenance && (
                <p style={{ margin: '6px 0 0 0', fontSize: '12px', color: '#666' }}>
                  Bowler Type Provenance: <code>{result.bowler_provenance.bowler_type}</code>
                </p>
              )}
            </div>
          </div>

          {/* 11 Placements Table */}
          <div style={{ border: '1px solid #ccc', borderRadius: '6px', overflow: 'hidden', backgroundColor: '#fff' }}>
            <div style={{ backgroundColor: '#f1f3f5', padding: '12px 16px', borderBottom: '1px solid #ddd' }}>
              <h3 style={{ margin: 0, fontSize: '15px' }}>Field Placements ({result.placements.length} Players)</h3>
            </div>
            <table id="placements-table" style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
              <thead>
                <tr style={{ backgroundColor: '#fafafa', borderBottom: '2px solid #ddd' }}>
                  <th style={{ padding: '10px 14px' }}>#</th>
                  <th style={{ padding: '10px 14px' }}>Position</th>
                  <th style={{ padding: '10px 14px' }}>Role</th>
                  <th style={{ padding: '10px 14px' }}>X (m)</th>
                  <th style={{ padding: '10px 14px' }}>Y (m)</th>
                  <th style={{ padding: '10px 14px' }}>Tactical Reason</th>
                </tr>
              </thead>
              <tbody>
                {result.placements.map((p, idx) => (
                  <tr key={idx} style={{ borderBottom: '1px solid #eee' }}>
                    <td style={{ padding: '9px 14px', color: '#666' }}>{idx + 1}</td>
                    <td style={{ padding: '9px 14px', fontWeight: 'bold' }}>{p.position_name}</td>
                    <td style={{ padding: '9px 14px' }}>
                      <span
                        style={{
                          padding: '2px 6px',
                          borderRadius: '3px',
                          fontSize: '11px',
                          backgroundColor: p.role === 'wicket_taking' ? '#ffe8e6' : p.role === 'core' ? '#e2e3e5' : '#e7f5ff',
                          color: p.role === 'wicket_taking' ? '#d9381e' : '#333',
                        }}
                      >
                        {p.role}
                      </span>
                    </td>
                    <td style={{ padding: '9px 14px', fontFamily: 'monospace' }}>{p.x.toFixed(1)}</td>
                    <td style={{ padding: '9px 14px', fontFamily: 'monospace' }}>{p.y.toFixed(1)}</td>
                    <td style={{ padding: '9px 14px', color: '#444' }}>{p.reason}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
