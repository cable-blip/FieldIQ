import React, { useState, useEffect } from 'react';
import { ThreeField, type FieldPlacement } from './ThreeField';

export interface PlayersResponse {
  batters: string[];
  bowlers: string[];
  tactical_objectives?: string[];
  match_formats?: string[];
}

export interface MatchupStats {
  has_history: boolean;
  balls_faced: number;
  runs_scored?: number;
  dismissals?: number;
  strike_rate?: number | null;
  dot_ball_pct?: number | null;
  boundary_pct?: number | null;
  source?: string;
  data_coverage_note?: string;
}

export interface ModelConfidence {
  status: string;
  wicket_recall: number;
  wicket_precision: number;
  message?: string;
}

export interface AnalysisResponse {
  analysis_id: string;
  status: string;
  data_driven: boolean;
  reason: string;
  placements: FieldPlacement[];
  ers: number;
  ewo: number;
  cds: number;
  tactical_explanations: string[];
  is_legal: boolean;
  violations: string[];
  matchup_stats: MatchupStats;
  data_coverage?: string;
  model_confidence?: ModelConfidence;
  bowler_provenance?: Record<string, string>;
  zone_chart?: Record<string, number>;
}

export const FieldIQ3DView: React.FC = () => {
  // Form options from backend
  const [availableBatters, setAvailableBatters] = useState<string[]>([]);
  const [availableBowlers, setAvailableBowlers] = useState<string[]>([]);
  const [tacticalObjectives, setTacticalObjectives] = useState<string[]>([
    'attack_wicket',
    'prevent_boundary',
    'build_pressure',
    'stop_singles',
  ]);

  // Form input state
  const [batterName, setBatterName] = useState<string>('Virat Kohli');
  const [bowlerName, setBowlerName] = useState<string>('Mohammad Asif');
  const [matchFormat, setMatchFormat] = useState<'T20' | 'ODI'>('T20');
  const [over, setOver] = useState<number>(3); // 1-indexed over: 3 = Over 3 (Powerplay)
  const [runs, setRuns] = useState<number>(28);
  const [wickets, setWickets] = useState<number>(0);
  const [tacticalObjective, setTacticalObjective] = useState<string>('attack_wicket');

  // Request & Result state
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AnalysisResponse | null>(null);

  // Fetch real players & authoritative enums on mount
  useEffect(() => {
    fetch('/api/v1/players')
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((data: PlayersResponse) => {
        if (data.batters && data.batters.length > 0) {
          setAvailableBatters(data.batters);
          if (!data.batters.includes(batterName)) {
            setBatterName(data.batters[0]);
          }
        }
        if (data.bowlers && data.bowlers.length > 0) {
          setAvailableBowlers(data.bowlers);
        }
        if (data.tactical_objectives && data.tactical_objectives.length > 0) {
          setTacticalObjectives(data.tactical_objectives);
        }
      })
      .catch((err) => {
        setError(`Failed to load player options: ${err.message}`);
      });
  }, []);

  const getPhaseName = (overNum: number, fmt: 'T20' | 'ODI'): string => {
    if (fmt === 'T20') {
      if (overNum <= 6) return 'Powerplay';
      if (overNum <= 15) return 'Middle';
      return 'Death';
    } else {
      if (overNum <= 10) return 'Powerplay';
      if (overNum <= 40) return 'Middle';
      return 'Death';
    }
  };

  const maxOvers = matchFormat === 'T20' ? 20 : 50;
  const overOptions = Array.from({ length: maxOvers }, (_, i) => i + 1);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    const payload = {
      batter_name: batterName,
      bowler_name: bowlerName,
      match_format: matchFormat,
      innings: 1,
      over: over,
      runs: Number(runs),
      wickets: Number(wickets),
      tactical_objective: tacticalObjective,
      ground_preset_id: 'standard',
    };

    try {
      const res = await fetch('/api/v1/analysis', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errBody = await res.json().catch(() => ({}));
        throw new Error(errBody.message || errBody.detail || `Server returned HTTP ${res.status}`);
      }

      const data: AnalysisResponse = await res.json();
      setResult(data);
    } catch (err: any) {
      setError(err.message || 'Unknown network error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ fontFamily: 'system-ui, -apple-system, sans-serif', maxWidth: '1400px', margin: '0 auto', padding: '1.5rem', color: '#f1f5f9', backgroundColor: '#0b0f19', minHeight: '100vh' }}>
      <header style={{ marginBottom: '1.5rem', borderBottom: '1px solid #1e293b', paddingBottom: '1rem' }}>
        <h1 style={{ margin: 0, fontSize: '1.6rem', color: '#38bdf8' }}>FieldIQ — 3D Cricket Tactical Intelligence</h1>
        <p style={{ margin: '0.25rem 0 0 0', color: '#94a3b8', fontSize: '0.9rem' }}>
          Interactive 3D Field Visualization, Server-Verified Rule Enforcement, and Transparent Uncertainty Disclosures
        </p>
      </header>

      {/* Control Form Bar */}
      <form onSubmit={handleSubmit} style={{ background: '#111827', padding: '1.25rem', borderRadius: '8px', border: '1px solid #1f2937', marginBottom: '1.5rem' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', alignItems: 'end' }}>
          {/* Batter Input */}
          <div>
            <label htmlFor="batter-select" style={{ display: 'block', fontSize: '0.8rem', color: '#94a3b8', marginBottom: '0.25rem' }}>
              Batter (9 Verified)
            </label>
            <select
              id="batter-select"
              value={batterName}
              onChange={(e) => setBatterName(e.target.value)}
              style={{ width: '100%', padding: '0.5rem', background: '#1f2937', color: '#f1f5f9', border: '1px solid #374151', borderRadius: '4px' }}
            >
              {availableBatters.map((b) => (
                <option key={b} value={b}>{b}</option>
              ))}
            </select>
          </div>

          {/* Bowler Input with Datalist */}
          <div>
            <label htmlFor="bowler-input" style={{ display: 'block', fontSize: '0.8rem', color: '#94a3b8', marginBottom: '0.25rem' }}>
              Bowler ({availableBowlers.length > 0 ? `${availableBowlers.length} Available` : '330 Available'})
            </label>
            <input
              id="bowler-input"
              list="bowler-options"
              value={bowlerName}
              onChange={(e) => setBowlerName(e.target.value)}
              style={{ width: '100%', padding: '0.5rem', background: '#1f2937', color: '#f1f5f9', border: '1px solid #374151', borderRadius: '4px' }}
              placeholder="Select or type bowler..."
            />
            <datalist id="bowler-options">
              {availableBowlers.map((b) => (
                <option key={b} value={b} />
              ))}
            </datalist>
          </div>

          {/* Format */}
          <div>
            <label htmlFor="format-select" style={{ display: 'block', fontSize: '0.8rem', color: '#94a3b8', marginBottom: '0.25rem' }}>
              Format
            </label>
            <select
              id="format-select"
              value={matchFormat}
              onChange={(e) => setMatchFormat(e.target.value as 'T20' | 'ODI')}
              style={{ width: '100%', padding: '0.5rem', background: '#1f2937', color: '#f1f5f9', border: '1px solid #374151', borderRadius: '4px' }}
            >
              <option value="T20">T20 (20 Overs)</option>
              <option value="ODI">ODI (50 Overs)</option>
            </select>
          </div>

          {/* Over Selection */}
          <div>
            <label htmlFor="over-select" style={{ display: 'block', fontSize: '0.8rem', color: '#94a3b8', marginBottom: '0.25rem' }}>
              Over ({getPhaseName(over, matchFormat)})
            </label>
            <select
              id="over-select"
              value={over}
              onChange={(e) => setOver(Number(e.target.value))}
              style={{ width: '100%', padding: '0.5rem', background: '#1f2937', color: '#f1f5f9', border: '1px solid #374151', borderRadius: '4px' }}
            >
              {overOptions.map((o) => (
                <option key={o} value={o}>Over {o} — {getPhaseName(o, matchFormat)}</option>
              ))}
            </select>
          </div>

          {/* Runs */}
          <div>
            <label htmlFor="runs-input" style={{ display: 'block', fontSize: '0.8rem', color: '#94a3b8', marginBottom: '0.25rem' }}>
              Team Runs
            </label>
            <input
              id="runs-input"
              type="number"
              min="0"
              value={runs}
              onChange={(e) => setRuns(Number(e.target.value))}
              style={{ width: '100%', padding: '0.5rem', background: '#1f2937', color: '#f1f5f9', border: '1px solid #374151', borderRadius: '4px' }}
            />
          </div>

          {/* Wickets */}
          <div>
            <label htmlFor="wickets-input" style={{ display: 'block', fontSize: '0.8rem', color: '#94a3b8', marginBottom: '0.25rem' }}>
              Wickets
            </label>
            <input
              id="wickets-input"
              type="number"
              min="0"
              max="10"
              value={wickets}
              onChange={(e) => setWickets(Number(e.target.value))}
              style={{ width: '100%', padding: '0.5rem', background: '#1f2937', color: '#f1f5f9', border: '1px solid #374151', borderRadius: '4px' }}
            />
          </div>

          {/* Tactical Objective */}
          <div>
            <label htmlFor="objective-select" style={{ display: 'block', fontSize: '0.8rem', color: '#94a3b8', marginBottom: '0.25rem' }}>
              Tactical Objective
            </label>
            <select
              id="objective-select"
              value={tacticalObjective}
              onChange={(e) => setTacticalObjective(e.target.value)}
              style={{ width: '100%', padding: '0.5rem', background: '#1f2937', color: '#f1f5f9', border: '1px solid #374151', borderRadius: '4px' }}
            >
              {tacticalObjectives.map((obj) => (
                <option key={obj} value={obj}>{obj}</option>
              ))}
            </select>
          </div>

          {/* Submit */}
          <div>
            <button
              id="submit-analysis"
              type="submit"
              disabled={loading}
              style={{
                width: '100%',
                padding: '0.6rem 1rem',
                background: loading ? '#475569' : '#0284c7',
                color: '#ffffff',
                border: 'none',
                borderRadius: '4px',
                fontWeight: 600,
                cursor: loading ? 'not-allowed' : 'pointer',
              }}
            >
              {loading ? 'Optimizing 3D Field...' : 'Generate 3D Tactical Field'}
            </button>
          </div>
        </div>
      </form>

      {error && (
        <div role="alert" style={{ background: '#7f1d1d', border: '1px solid #ef4444', color: '#fecaca', padding: '1rem', borderRadius: '6px', marginBottom: '1.5rem' }}>
          <strong>Error:</strong> {error}
        </div>
      )}

      {/* Main 3D Layout & Tactical Readout */}
      {result && (
        <section aria-label="Tactical Results" style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {/* Server-Verified Legality Banner (Display-only: no client recomputation) */}
          <div
            id="legality-banner"
            style={{
              padding: '0.85rem 1.25rem',
              borderRadius: '6px',
              border: result.is_legal ? '1px solid #10b981' : '1px solid #ef4444',
              background: result.is_legal ? '#064e3b' : '#7f1d1d',
              color: result.is_legal ? '#6ee7b7' : '#fecaca',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            }}
          >
            <div>
              <span style={{ fontWeight: 700, marginRight: '0.75rem' }}>
                {result.is_legal ? '✓ LEGAL FIELD CONFIGURATION' : '⚠ FIELD RESTRICTION VIOLATION'}
              </span>
              <span style={{ fontSize: '0.85rem' }}>
                {result.is_legal ? 'Complies with all ICC fielding regulations' : `${result.violations.length} violation(s) detected`}
              </span>
            </div>
            <span style={{ fontSize: '0.8rem', background: '#00000044', padding: '0.2rem 0.6rem', borderRadius: '4px' }}>
              {matchFormat} · Over {over} ({getPhaseName(over, matchFormat)})
            </span>
          </div>

          {result.violations && result.violations.length > 0 && (
            <div style={{ background: '#450a0a', border: '1px solid #b91c1c', padding: '0.75rem', borderRadius: '4px', color: '#fca5a5', fontSize: '0.85rem' }}>
              <strong>Server-Reported Violations:</strong>
              <ul style={{ margin: '0.25rem 0 0 1.25rem', padding: 0 }}>
                {result.violations.map((v, i) => (
                  <li key={i}>{v}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Split: 3D Canvas (Left) + Tactical Cards (Right) */}
          <div style={{ display: 'grid', gridTemplateColumns: 'minmax(400px, 1.8fr) minmax(320px, 1fr)', gap: '1.5rem', alignItems: 'start' }}>
            {/* 3D WebGL Canvas Container */}
            <div
              id="canvas-container"
              style={{
                position: 'relative',
                height: '560px',
                background: '#04070e',
                borderRadius: '8px',
                border: '1px solid #1e293b',
                overflow: 'hidden',
              }}
            >
              <ThreeField
                fielders={result.placements}
                zoneChart={result.zone_chart}
                venueId="standard"
                pitchType="standard"
              />
            </div>

            {/* Tactical Intelligence Cards */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {/* Data Coverage Card */}
              <div id="data-coverage-card" style={{ background: '#111827', padding: '1rem', borderRadius: '6px', border: '1px solid #1f2937' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                  <span style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: '#94a3b8', letterSpacing: '0.05em' }}>
                    Matchup Intelligence Tier
                  </span>
                  <span style={{ fontSize: '0.8rem', fontWeight: 600, color: '#38bdf8', background: '#0369a122', padding: '0.2rem 0.5rem', borderRadius: '4px', border: '1px solid #0284c7' }}>
                    {result.data_coverage || result.matchup_stats.source || 'insufficient_data'}
                  </span>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0.5rem', textAlign: 'center', margin: '0.75rem 0' }}>
                  <div style={{ background: '#1f2937', padding: '0.5rem', borderRadius: '4px' }}>
                    <div style={{ fontSize: '0.7rem', color: '#94a3b8' }}>Balls Faced</div>
                    <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#f1f5f9' }}>{result.matchup_stats.balls_faced}</div>
                  </div>
                  <div style={{ background: '#1f2937', padding: '0.5rem', borderRadius: '4px' }}>
                    <div style={{ fontSize: '0.7rem', color: '#94a3b8' }}>Strike Rate</div>
                    <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#f1f5f9' }}>
                      {result.matchup_stats.strike_rate !== null ? result.matchup_stats.strike_rate : 'N/A'}
                    </div>
                  </div>
                  <div style={{ background: '#1f2937', padding: '0.5rem', borderRadius: '4px' }}>
                    <div style={{ fontSize: '0.7rem', color: '#94a3b8' }}>Dot Ball %</div>
                    <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#f1f5f9' }}>
                      {result.matchup_stats.dot_ball_pct !== null ? `${result.matchup_stats.dot_ball_pct}%` : 'N/A'}
                    </div>
                  </div>
                </div>
                {result.matchup_stats.data_coverage_note && (
                  <p style={{ margin: 0, fontSize: '0.75rem', color: '#94a3b8', fontStyle: 'italic' }}>
                    {result.matchup_stats.data_coverage_note}
                  </p>
                )}
              </div>

              {/* Model Confidence Disclosure Card */}
              {result.model_confidence && (
                <div id="model-confidence-card" style={{ background: '#111827', padding: '1rem', borderRadius: '6px', border: '1px solid #1f2937' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                    <span style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: '#94a3b8', letterSpacing: '0.05em' }}>
                      Model Confidence Disclosure
                    </span>
                    <span style={{ fontSize: '0.75rem', fontWeight: 600, color: '#f59e0b', background: '#d9770622', padding: '0.2rem 0.5rem', borderRadius: '4px', border: '1px solid #d97706' }}>
                      {result.model_confidence.status}
                    </span>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem', textAlign: 'center', margin: '0.75rem 0' }}>
                    <div style={{ background: '#1f2937', padding: '0.5rem', borderRadius: '4px' }}>
                      <div style={{ fontSize: '0.7rem', color: '#94a3b8' }}>Wicket Recall</div>
                      <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#fbbf24' }}>
                        {(result.model_confidence.wicket_recall * 100).toFixed(1)}%
                      </div>
                    </div>
                    <div style={{ background: '#1f2937', padding: '0.5rem', borderRadius: '4px' }}>
                      <div style={{ fontSize: '0.7rem', color: '#94a3b8' }}>Wicket Precision</div>
                      <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#fbbf24' }}>
                        {(result.model_confidence.wicket_precision * 100).toFixed(1)}%
                      </div>
                    </div>
                  </div>
                  <p style={{ margin: 0, fontSize: '0.75rem', color: '#94a3b8', lineHeight: 1.4 }}>
                    {result.model_confidence.message ||
                      'Baseline ML probability model output. The system is decision-support software and does not predict outcomes with certainty.'}
                  </p>
                </div>
              )}

              {/* Expected Metrics */}
              <div style={{ background: '#111827', padding: '1rem', borderRadius: '6px', border: '1px solid #1f2937' }}>
                <span style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: '#94a3b8', letterSpacing: '0.05em', display: 'block', marginBottom: '0.5rem' }}>
                  Optimization Scores
                </span>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0.5rem', textAlign: 'center' }}>
                  <div style={{ background: '#1f2937', padding: '0.5rem', borderRadius: '4px' }}>
                    <div style={{ fontSize: '0.7rem', color: '#94a3b8' }}>ERS (Runs Saved)</div>
                    <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#38bdf8' }}>{result.ers.toFixed(2)}</div>
                  </div>
                  <div style={{ background: '#1f2937', padding: '0.5rem', borderRadius: '4px' }}>
                    <div style={{ fontSize: '0.7rem', color: '#94a3b8' }}>EWO (Wicket Opp)</div>
                    <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#34d399' }}>{result.ewo.toFixed(2)}</div>
                  </div>
                  <div style={{ background: '#1f2937', padding: '0.5rem', borderRadius: '4px' }}>
                    <div style={{ fontSize: '0.7rem', color: '#94a3b8' }}>CDS (Coverage)</div>
                    <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#a78bfa' }}>{result.cds.toFixed(2)}</div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* 11-Fielder Placements Table */}
          <div style={{ background: '#111827', borderRadius: '8px', border: '1px solid #1f2937', overflow: 'hidden' }}>
            <div style={{ padding: '0.75rem 1rem', borderBottom: '1px solid #1f2937', background: '#1e293b', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontWeight: 600, fontSize: '0.95rem' }}>11 Recommended Field Placements</span>
              <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>Total Fielders: {result.placements.length}</span>
            </div>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem', textAlign: 'left' }}>
                <thead>
                  <tr style={{ background: '#0f172a', color: '#94a3b8', borderBottom: '1px solid #1f2937' }}>
                    <th style={{ padding: '0.6rem 0.8rem' }}>#</th>
                    <th style={{ padding: '0.6rem 0.8rem' }}>Position Name</th>
                    <th style={{ padding: '0.6rem 0.8rem' }}>X (m)</th>
                    <th style={{ padding: '0.6rem 0.8rem' }}>Y (m)</th>
                    <th style={{ padding: '0.6rem 0.8rem' }}>Role</th>
                    <th style={{ padding: '0.6rem 0.8rem' }}>Tactical Reason</th>
                  </tr>
                </thead>
                <tbody>
                  {result.placements.map((p, idx) => (
                    <tr key={idx} style={{ borderBottom: '1px solid #1f2937', background: idx % 2 === 0 ? '#111827' : '#131d2e' }}>
                      <td style={{ padding: '0.6rem 0.8rem', color: '#64748b' }}>{idx + 1}</td>
                      <td style={{ padding: '0.6rem 0.8rem', fontWeight: 600, color: '#38bdf8' }}>{p.position_name}</td>
                      <td style={{ padding: '0.6rem 0.8rem', fontFamily: 'monospace' }}>{p.x.toFixed(1)}</td>
                      <td style={{ padding: '0.6rem 0.8rem', fontFamily: 'monospace' }}>{p.y.toFixed(1)}</td>
                      <td style={{ padding: '0.6rem 0.8rem' }}>
                        <span
                          style={{
                            padding: '0.15rem 0.4rem',
                            borderRadius: '3px',
                            fontSize: '0.75rem',
                            background:
                              p.role === 'wicket_taking'
                                ? '#7f1d1d'
                                : p.role === 'core'
                                ? '#064e3b'
                                : '#1e3a8a',
                            color:
                              p.role === 'wicket_taking'
                                ? '#fecaca'
                                : p.role === 'core'
                                ? '#a7f3d0'
                                : '#bfdbfe',
                          }}
                        >
                          {p.role}
                        </span>
                      </td>
                      <td style={{ padding: '0.6rem 0.8rem', color: '#cbd5e1' }}>{p.reason || 'Tactical positioning'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>
      )}
    </div>
  );
};
