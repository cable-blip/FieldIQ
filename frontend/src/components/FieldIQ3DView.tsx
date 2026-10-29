import React, { useState, useEffect, useMemo } from 'react';
import { ThreeField, type FieldPlacement } from './ThreeField';
import { LiveDeliveryConsole, type LoggedDelivery } from './LiveDeliveryConsole';
import { GameplanTimeline, type GameplanOverItem } from './GameplanTimeline';
import { DatasetStudioModal } from './DatasetStudioModal';

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

export interface EvaluationResponse {
  ers: number;
  ewo: number;
  cds: number;
  is_legal: boolean;
  violations: string[];
  data_coverage?: string;
  model_confidence?: any;
}

export const FieldIQ3DView: React.FC = () => {
  // Navigation Mode
  const [activeTab, setActiveTab] = useState<'analysis' | 'live' | 'gameplan'>('analysis');
  const [datasetModalOpen, setDatasetModalOpen] = useState<boolean>(false);

  // Form options from backend
  const [availableBatters, setAvailableBatters] = useState<string[]>([]);
  const [availableBowlers, setAvailableBowlers] = useState<string[]>([]);
  const [tacticalObjectives, setTacticalObjectives] = useState<string[]>([
    'attack_wicket',
    'prevent_boundary',
    'build_pressure',
    'stop_singles',
  ]);
  const [groundPresets, setGroundPresets] = useState<Array<{ id: string; name: string }>>([
    { id: 'standard', name: 'Standard Oval' },
    { id: 'lords', name: "Lord's (London)" },
    { id: 'mcg', name: 'MCG (Melbourne)' },
    { id: 'eden_park', name: 'Eden Park (Auckland)' },
    { id: 'wankhede', name: 'Wankhede (Mumbai)' },
    { id: 'adelaide', name: 'Adelaide Oval' },
  ]);

  // Form input state
  const [batterName, setBatterName] = useState<string>('Virat Kohli');
  const [bowlerName, setBowlerName] = useState<string>('Mohammad Asif');
  const [matchFormat, setMatchFormat] = useState<'T20' | 'ODI'>('T20');
  const [over, setOver] = useState<number>(3); // 1-indexed over: 3 = Over 3 (Powerplay)
  const [ball, setBall] = useState<number>(1);
  const [runs, setRuns] = useState<number>(28);
  const [wickets, setWickets] = useState<number>(0);
  const [tacticalObjective, setTacticalObjective] = useState<string>('attack_wicket');
  const [groundPresetId, setGroundPresetId] = useState<string>('standard');

  // Request & Result state
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AnalysisResponse | null>(null);

  // What-If human-in-the-loop state
  const [originalPlacements, setOriginalPlacements] = useState<FieldPlacement[]>([]);
  const [editedPlacements, setEditedPlacements] = useState<FieldPlacement[]>([]);
  const [selectedFielderIndex, setSelectedFielderIndex] = useState<number | null>(null);
  const [evaluation, setEvaluation] = useState<EvaluationResponse | null>(null);
  const [evaluationLoading, setEvaluationLoading] = useState<boolean>(false);
  const [evaluationStale, setEvaluationStale] = useState<boolean>(false);
  const [evaluationError, setEvaluationError] = useState<string | null>(null);

  // Live match session state
  const [deliveryHistory, setDeliveryHistory] = useState<LoggedDelivery[]>([]);
  const [liveCommentary, setLiveCommentary] = useState<string>('');
  const [tacticalAdjustment, setTacticalAdjustment] = useState<string>('');

  // Gameplan multi-over sequence state
  const [gameplanSequence, setGameplanSequence] = useState<GameplanOverItem[]>([]);
  const [activeGameplanOverIndex, setActiveGameplanOverIndex] = useState<number>(0);
  const [gameplanLoading, setGameplanLoading] = useState<boolean>(false);
  const [plannedOvers, setPlannedOvers] = useState<number>(5);

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

    fetch('/api/v1/grounds/presets')
      .then((res) => (res.ok ? res.json() : []))
      .then((presets) => {
        if (Array.isArray(presets) && presets.length > 0) {
          setGroundPresets(presets.map((p) => ({ id: p.id, name: p.name })));
        }
      })
      .catch(() => {
        // Fall back gracefully to standard presets
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

  // Check if current placements differ from original server recommendation
  const isPlacementModified = (index: number): boolean => {
    if (!originalPlacements[index] || !editedPlacements[index]) return false;
    const orig = originalPlacements[index];
    const curr = editedPlacements[index];
    return Math.abs(orig.x - curr.x) > 0.05 || Math.abs(orig.y - curr.y) > 0.05;
  };

  const anyPlacementsModified = useMemo(() => {
    if (originalPlacements.length === 0 || editedPlacements.length === 0) return false;
    return editedPlacements.some((_, idx) => isPlacementModified(idx));
  }, [originalPlacements, editedPlacements]);

  // Handle tactical analysis request
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setEvaluation(null);
    setEvaluationStale(false);
    setEvaluationError(null);

    const payload = {
      batter_name: batterName,
      bowler_name: bowlerName,
      match_format: matchFormat,
      innings: 1,
      over: over,
      runs: Number(runs),
      wickets: Number(wickets),
      tactical_objective: tacticalObjective,
      ground_preset_id: groundPresetId,
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
      const clonedPlacements = JSON.parse(JSON.stringify(data.placements));
      setOriginalPlacements(clonedPlacements);
      setEditedPlacements(JSON.parse(JSON.stringify(data.placements)));
      setSelectedFielderIndex(0);
    } catch (err: any) {
      setError(err.message || 'Unknown network error');
    } finally {
      setLoading(false);
    }
  };

  // Update a single placement coordinate (from table input or 3D drag)
  const updatePlacementCoordinate = (index: number, coordinate: 'x' | 'y', value: string | number) => {
    const numericValue = typeof value === 'number' ? value : Number(value);
    if (!Number.isFinite(numericValue)) return;

    setEditedPlacements((current) =>
      current.map((placement, placementIndex) =>
        placementIndex === index ? { ...placement, [coordinate]: Math.round(numericValue * 10) / 10 } : placement
      )
    );
    if (evaluation) {
      setEvaluationStale(true);
    }
  };

  // Update placement coordinate by position name (used by 3D marker drag)
  const handleUpdateFielderFrom3D = (name: string, newX: number, newY: number) => {
    setEditedPlacements((current) =>
      current.map((placement) => {
        const matchesName =
          placement.position_name === name || placement.name === name || placement.fielder?.name === name;
        if (matchesName) {
          return {
            ...placement,
            x: Math.round(newX * 10) / 10,
            y: Math.round(newY * 10) / 10,
          };
        }
        return placement;
      })
    );
    if (evaluation) {
      setEvaluationStale(true);
    }
  };

  // Reset to original server recommendation
  const handleResetToRecommendation = () => {
    if (originalPlacements.length > 0) {
      setEditedPlacements(JSON.parse(JSON.stringify(originalPlacements)));
      setEvaluationStale(false);
      setEvaluation(null);
      setEvaluationError(null);
    }
  };

  // Evaluate edited field via server POST /api/v1/analysis/evaluate
  const evaluateEditedField = async () => {
    if (!result) return;

    // Check if fielder capability data is present without fabricating
    const missingCapabilities = editedPlacements.some((p) => !p.fielder);
    if (missingCapabilities) {
      setEvaluationError('Evaluation disabled: server-provided fielder capabilities are absent from placement data.');
      return;
    }

    setEvaluationLoading(true);
    setEvaluationError(null);

    try {
      const response = await fetch('/api/v1/analysis/evaluate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          batter_name: batterName,
          bowler_name: bowlerName,
          match_format: matchFormat,
          over: over,
          placements: editedPlacements,
          ground_preset_id: groundPresetId,
        }),
      });

      const body = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(body.message || body.detail || `Server returned HTTP ${response.status}`);
      }

      setEvaluation(body as EvaluationResponse);
      setEvaluationStale(false);
    } catch (err: any) {
      setEvaluationError(err.message || 'Unable to evaluate the edited field.');
    } finally {
      setEvaluationLoading(false);
    }
  };

  // Generate multi-over gameplan via server POST /api/v1/analysis/gameplan
  const handleGenerateGameplan = async () => {
    setGameplanLoading(true);
    setError(null);
    try {
      const response = await fetch('/api/v1/analysis/gameplan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          batter_name: batterName,
          bowler_name: bowlerName,
          match_format: matchFormat,
          current_over: over,
          runs: runs,
          wickets: wickets,
          planned_overs: plannedOvers,
          tactical_objective: tacticalObjective,
          ground_preset_id: groundPresetId,
        }),
      });

      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body.message || body.detail || `Server returned HTTP ${response.status}`);
      }

      const data = await response.json();
      if (data.gameplan_sequence && data.gameplan_sequence.length > 0) {
        setGameplanSequence(data.gameplan_sequence);
        setActiveGameplanOverIndex(0);
        // Switch 3D field to first gameplan over placements
        if (data.gameplan_sequence[0].placements) {
          setEditedPlacements(data.gameplan_sequence[0].placements);
        }
      }
    } catch (err: any) {
      setError(err.message || 'Failed to generate gameplan.');
    } finally {
      setGameplanLoading(false);
    }
  };

  // Live match delivery event handler
  const handleLiveDeliveryLogged = (data: any) => {
    if (data.current_score) {
      setRuns(data.current_score.runs);
      setWickets(data.current_score.wickets);
      setOver(data.current_score.over);
      setBall(data.current_score.ball);
    }
    if (data.field_placements && data.field_placements.length > 0) {
      setEditedPlacements(data.field_placements);
      if (result) {
        setResult({ ...result, placements: data.field_placements, is_legal: data.is_legal });
      }
    }
    if (data.zone_chart && result) {
      setResult((prev) => (prev ? { ...prev, zone_chart: data.zone_chart } : prev));
    }
    if (data.tactical_adjustment) {
      setTacticalAdjustment(data.tactical_adjustment);
    }
    if (data.commentary) {
      setLiveCommentary(data.commentary);
    }
    if (data.delivery_history) {
      setDeliveryHistory(data.delivery_history);
    }
  };

  const handleLiveUndo = (data: any) => {
    if (data.current_score) {
      setRuns(data.current_score.runs);
      setWickets(data.current_score.wickets);
      setOver(data.current_score.over);
      setBall(data.current_score.ball);
    }
    if (data.field_placements) {
      setEditedPlacements(data.field_placements);
    }
    if (data.delivery_history) {
      setDeliveryHistory(data.delivery_history);
    }
  };

  const handleLiveReset = (data: any) => {
    if (data.current_score) {
      setRuns(data.current_score.runs);
      setWickets(data.current_score.wickets);
      setOver(data.current_score.over);
      setBall(data.current_score.ball);
    }
    setDeliveryHistory([]);
    setLiveCommentary('Live match session reset. Spell ready.');
    setTacticalAdjustment('');
  };

  const selectedPlacement =
    selectedFielderIndex !== null && editedPlacements[selectedFielderIndex]
      ? editedPlacements[selectedFielderIndex]
      : null;

  return (
    <div
      style={{
        fontFamily: 'system-ui, -apple-system, sans-serif',
        maxWidth: '1440px',
        margin: '0 auto',
        padding: '1.25rem',
        color: '#f1f5f9',
        backgroundColor: '#0b0f19',
        minHeight: '100vh',
      }}
    >
      {/* Top Header Strip */}
      <header
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '1.25rem',
          borderBottom: '1px solid #1e293b',
          paddingBottom: '0.85rem',
          flexWrap: 'wrap',
          gap: '0.75rem',
        }}
      >
        <div>
          <h1 style={{ margin: 0, fontSize: '1.5rem', color: '#38bdf8', letterSpacing: '-0.02em' }}>
            FieldIQ — 3D Cricket Tactical Intelligence
          </h1>
          <p style={{ margin: '0.2rem 0 0 0', color: '#94a3b8', fontSize: '0.85rem' }}>
            Interactive 3D Spatial Intelligence · Server-Authoritative Legality · Human-in-the-Loop Operator Console
          </p>
        </div>

        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          <button
            type="button"
            id="dataset-studio-btn"
            onClick={() => setDatasetModalOpen(true)}
            style={{
              padding: '0.45rem 0.85rem',
              background: '#1e293b',
              color: '#38bdf8',
              border: '1px solid #334155',
              borderRadius: '6px',
              fontSize: '0.8rem',
              fontWeight: 600,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '0.4rem',
            }}
          >
            📊 Dataset Studio & Lineage
          </button>
        </div>
      </header>

      {/* Primary Workflow Navigation Tabs */}
      <nav
        aria-label="Workflow Navigation"
        style={{
          display: 'flex',
          gap: '0.5rem',
          marginBottom: '1.25rem',
          borderBottom: '1px solid #1f2937',
          paddingBottom: '0.5rem',
        }}
      >
        <button
          type="button"
          onClick={() => setActiveTab('analysis')}
          style={{
            padding: '0.5rem 1rem',
            background: activeTab === 'analysis' ? '#0284c7' : '#111827',
            color: activeTab === 'analysis' ? '#ffffff' : '#94a3b8',
            border: activeTab === 'analysis' ? '1px solid #38bdf8' : '1px solid #1f2937',
            borderRadius: '6px',
            fontSize: '0.85rem',
            fontWeight: 600,
            cursor: 'pointer',
          }}
        >
          🎯 3D Tactical Field & What-If
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('live')}
          style={{
            padding: '0.5rem 1rem',
            background: activeTab === 'live' ? '#0284c7' : '#111827',
            color: activeTab === 'live' ? '#ffffff' : '#94a3b8',
            border: activeTab === 'live' ? '1px solid #38bdf8' : '1px solid #1f2937',
            borderRadius: '6px',
            fontSize: '0.85rem',
            fontWeight: 600,
            cursor: 'pointer',
          }}
        >
          ⚡ Live Ball-by-Ball Engine
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('gameplan')}
          style={{
            padding: '0.5rem 1rem',
            background: activeTab === 'gameplan' ? '#0284c7' : '#111827',
            color: activeTab === 'gameplan' ? '#ffffff' : '#94a3b8',
            border: activeTab === 'gameplan' ? '1px solid #38bdf8' : '1px solid #1f2937',
            borderRadius: '6px',
            fontSize: '0.85rem',
            fontWeight: 600,
            cursor: 'pointer',
          }}
        >
          📋 Multi-Over Strategic Gameplan
        </button>
      </nav>

      {/* Control Form Bar (Common Match Context) */}
      <form
        onSubmit={handleSubmit}
        style={{
          background: '#111827',
          padding: '1.25rem',
          borderRadius: '8px',
          border: '1px solid #1f2937',
          marginBottom: '1.5rem',
        }}
      >
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
            gap: '1rem',
            alignItems: 'end',
          }}
        >
          {/* Batter Input */}
          <div>
            <label
              htmlFor="batter-select"
              style={{ display: 'block', fontSize: '0.8rem', color: '#94a3b8', marginBottom: '0.25rem' }}
            >
              Batter (9 Verified)
            </label>
            <select
              id="batter-select"
              value={batterName}
              onChange={(e) => setBatterName(e.target.value)}
              style={{
                width: '100%',
                padding: '0.5rem',
                background: '#1f2937',
                color: '#f1f5f9',
                border: '1px solid #374151',
                borderRadius: '4px',
              }}
            >
              {availableBatters.map((b) => (
                <option key={b} value={b}>
                  {b}
                </option>
              ))}
            </select>
          </div>

          {/* Bowler Input with Datalist */}
          <div>
            <label
              htmlFor="bowler-input"
              style={{ display: 'block', fontSize: '0.8rem', color: '#94a3b8', marginBottom: '0.25rem' }}
            >
              Bowler ({availableBowlers.length > 0 ? `${availableBowlers.length} Available` : '330 Available'})
            </label>
            <input
              id="bowler-input"
              list="bowler-options"
              value={bowlerName}
              onChange={(e) => setBowlerName(e.target.value)}
              style={{
                width: '100%',
                padding: '0.5rem',
                background: '#1f2937',
                color: '#f1f5f9',
                border: '1px solid #374151',
                borderRadius: '4px',
              }}
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
            <label
              htmlFor="format-select"
              style={{ display: 'block', fontSize: '0.8rem', color: '#94a3b8', marginBottom: '0.25rem' }}
            >
              Format
            </label>
            <select
              id="format-select"
              value={matchFormat}
              onChange={(e) => setMatchFormat(e.target.value as 'T20' | 'ODI')}
              style={{
                width: '100%',
                padding: '0.5rem',
                background: '#1f2937',
                color: '#f1f5f9',
                border: '1px solid #374151',
                borderRadius: '4px',
              }}
            >
              <option value="T20">T20 (20 Overs)</option>
              <option value="ODI">ODI (50 Overs)</option>
            </select>
          </div>

          {/* Over Selection */}
          <div>
            <label
              htmlFor="over-select"
              style={{ display: 'block', fontSize: '0.8rem', color: '#94a3b8', marginBottom: '0.25rem' }}
            >
              Over ({getPhaseName(over, matchFormat)})
            </label>
            <select
              id="over-select"
              value={over}
              onChange={(e) => setOver(Number(e.target.value))}
              style={{
                width: '100%',
                padding: '0.5rem',
                background: '#1f2937',
                color: '#f1f5f9',
                border: '1px solid #374151',
                borderRadius: '4px',
              }}
            >
              {overOptions.map((o) => (
                <option key={o} value={o}>
                  Over {o} — {getPhaseName(o, matchFormat)}
                </option>
              ))}
            </select>
          </div>

          {/* Runs */}
          <div>
            <label
              htmlFor="runs-input"
              style={{ display: 'block', fontSize: '0.8rem', color: '#94a3b8', marginBottom: '0.25rem' }}
            >
              Team Runs
            </label>
            <input
              id="runs-input"
              type="number"
              min="0"
              value={runs}
              onChange={(e) => setRuns(Number(e.target.value))}
              style={{
                width: '100%',
                padding: '0.5rem',
                background: '#1f2937',
                color: '#f1f5f9',
                border: '1px solid #374151',
                borderRadius: '4px',
              }}
            />
          </div>

          {/* Wickets */}
          <div>
            <label
              htmlFor="wickets-input"
              style={{ display: 'block', fontSize: '0.8rem', color: '#94a3b8', marginBottom: '0.25rem' }}
            >
              Wickets
            </label>
            <input
              id="wickets-input"
              type="number"
              min="0"
              max="10"
              value={wickets}
              onChange={(e) => setWickets(Number(e.target.value))}
              style={{
                width: '100%',
                padding: '0.5rem',
                background: '#1f2937',
                color: '#f1f5f9',
                border: '1px solid #374151',
                borderRadius: '4px',
              }}
            />
          </div>

          {/* Tactical Objective */}
          <div>
            <label
              htmlFor="objective-select"
              style={{ display: 'block', fontSize: '0.8rem', color: '#94a3b8', marginBottom: '0.25rem' }}
            >
              Tactical Objective
            </label>
            <select
              id="objective-select"
              value={tacticalObjective}
              onChange={(e) => setTacticalObjective(e.target.value)}
              style={{
                width: '100%',
                padding: '0.5rem',
                background: '#1f2937',
                color: '#f1f5f9',
                border: '1px solid #374151',
                borderRadius: '4px',
              }}
            >
              {tacticalObjectives.map((obj) => (
                <option key={obj} value={obj}>
                  {obj}
                </option>
              ))}
            </select>
          </div>

          {/* Ground Venue Preset */}
          <div>
            <label
              htmlFor="ground-select"
              style={{ display: 'block', fontSize: '0.8rem', color: '#94a3b8', marginBottom: '0.25rem' }}
            >
              Venue Preset
            </label>
            <select
              id="ground-select"
              value={groundPresetId}
              onChange={(e) => setGroundPresetId(e.target.value)}
              style={{
                width: '100%',
                padding: '0.5rem',
                background: '#1f2937',
                color: '#f1f5f9',
                border: '1px solid #374151',
                borderRadius: '4px',
              }}
            >
              {groundPresets.map((g) => (
                <option key={g.id} value={g.id}>
                  {g.name}
                </option>
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
        <div
          role="alert"
          style={{
            background: '#7f1d1d',
            border: '1px solid #ef4444',
            color: '#fecaca',
            padding: '1rem',
            borderRadius: '6px',
            marginBottom: '1.5rem',
          }}
        >
          <strong>Error:</strong> {error}
        </div>
      )}

      {/* Main Mode 1: 3D Tactical Field & What-If */}
      {activeTab === 'analysis' && result && (
        <section aria-label="Tactical Results" style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {/* Dataset Lineage & Provenance Transparency Banner */}
          <div
            id="dataset-lineage-banner"
            style={{
              padding: '0.65rem 1.25rem',
              borderRadius: '6px',
              border: '1px solid #1e3a8a',
              background: '#0b1329',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              flexWrap: 'wrap',
              gap: '0.5rem',
              fontSize: '0.78rem',
              color: '#94a3b8',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
              <strong style={{ color: '#e2e8f0' }}>Dataset Lineage:</strong>
              <span>Spatial: <strong style={{ color: '#38bdf8' }}>rishsriv/t20i_data</strong> (ESPNcricinfo wagon wheels)</span>
              <span>·</span>
              <span>Context: <strong style={{ color: '#34d399' }}>Cricsheet</strong> (ball-by-ball & dismissals)</span>
            </div>
            <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }}>
              <span style={{ background: '#1e293b', color: '#cbd5e1', padding: '0.15rem 0.45rem', borderRadius: '3px', border: '1px solid #334155', fontSize: '0.7rem' }}>
                Derived historical dataset
              </span>
              <span style={{ background: '#064e3b44', color: '#34d399', padding: '0.15rem 0.45rem', borderRadius: '3px', border: '1px solid #059669', fontSize: '0.7rem' }}>
                Direction recorded; distance not measured
              </span>
              <span style={{ background: '#581c8744', color: '#c084fc', padding: '0.15rem 0.45rem', borderRadius: '3px', border: '1px solid #7c3aed', fontSize: '0.7rem' }}>
                Decision-support output
              </span>
            </div>
          </div>

          {/* Server-Verified Legality Banner (Authoritative from backend) */}
          <div
            id="legality-banner"
            style={{
              padding: '0.85rem 1.25rem',
              borderRadius: '6px',
              border: (evaluation ? evaluation.is_legal : result.is_legal) ? '1px solid #10b981' : '1px solid #ef4444',
              background: (evaluation ? evaluation.is_legal : result.is_legal) ? '#064e3b' : '#7f1d1d',
              color: (evaluation ? evaluation.is_legal : result.is_legal) ? '#6ee7b7' : '#fecaca',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              flexWrap: 'wrap',
              gap: '0.5rem',
            }}
          >
            <div>
              <span style={{ fontWeight: 700, marginRight: '0.75rem' }}>
                {(evaluation ? evaluation.is_legal : result.is_legal)
                  ? '✓ LEGAL FIELD CONFIGURATION'
                  : '⚠ FIELD RESTRICTION VIOLATION'}
              </span>
              <span style={{ fontSize: '0.85rem' }}>
                {(evaluation ? evaluation.is_legal : result.is_legal)
                  ? 'Complies with all ICC fielding regulations'
                  : `${(evaluation ? evaluation.violations : result.violations).length} violation(s) detected`}
              </span>
            </div>
            <span style={{ fontSize: '0.8rem', background: '#00000044', padding: '0.2rem 0.6rem', borderRadius: '4px' }}>
              {matchFormat} · Over {over} ({getPhaseName(over, matchFormat)}) · {evaluation ? 'Evaluated Field' : 'Server Recommended'}
            </span>
          </div>

          {(evaluation ? evaluation.violations : result.violations).length > 0 && (
            <div
              style={{
                background: '#450a0a',
                border: '1px solid #b91c1c',
                padding: '0.75rem',
                borderRadius: '4px',
                color: '#fca5a5',
                fontSize: '0.85rem',
              }}
            >
              <strong>Server-Reported Violations:</strong>
              <ul style={{ margin: '0.25rem 0 0 1.25rem', padding: 0 }}>
                {(evaluation ? evaluation.violations : result.violations).map((v, i) => (
                  <li key={i}>{v}</li>
                ))}
              </ul>
            </div>
          )}

          {/* 3D Canvas (Left) + Tactical Intelligence Panels (Right) */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'minmax(400px, 1.8fr) minmax(320px, 1fr)',
              gap: '1.5rem',
              alignItems: 'start',
            }}
          >
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
                fielders={editedPlacements.length > 0 ? editedPlacements : result.placements}
                zoneChart={result.zone_chart}
                venueId={groundPresetId}
                pitchType="standard"
                selectedFielderIndex={selectedFielderIndex}
                onSelectFielder={(idx) => setSelectedFielderIndex(idx)}
                onUpdateFielder={handleUpdateFielderFrom3D}
              />
            </div>

            {/* Tactical Intelligence Cards */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {/* Matchup Intelligence Tier Card */}
              <div
                id="data-coverage-card"
                style={{ background: '#111827', padding: '1rem', borderRadius: '6px', border: '1px solid #1f2937' }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                  <span style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: '#94a3b8', letterSpacing: '0.05em' }}>
                    Matchup Intelligence Tier
                  </span>
                  <span
                    style={{
                      fontSize: '0.8rem',
                      fontWeight: 600,
                      color: '#38bdf8',
                      background: '#0369a122',
                      padding: '0.2rem 0.5rem',
                      borderRadius: '4px',
                      border: '1px solid #0284c7',
                    }}
                  >
                    {result.data_coverage || result.matchup_stats.source || 'insufficient_data'}
                  </span>
                </div>
                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(3, 1fr)',
                    gap: '0.5rem',
                    textAlign: 'center',
                    margin: '0.75rem 0',
                  }}
                >
                  <div style={{ background: '#1f2937', padding: '0.5rem', borderRadius: '4px' }}>
                    <div style={{ fontSize: '0.7rem', color: '#94a3b8' }}>Balls Faced</div>
                    <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#f1f5f9' }}>
                      {result.matchup_stats.balls_faced}
                    </div>
                  </div>
                  <div style={{ background: '#1f2937', padding: '0.5rem', borderRadius: '4px' }}>
                    <div style={{ fontSize: '0.7rem', color: '#94a3b8' }}>Strike Rate</div>
                    <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#f1f5f9' }}>
                      {result.matchup_stats.strike_rate !== null && result.matchup_stats.strike_rate !== undefined
                        ? result.matchup_stats.strike_rate
                        : 'N/A'}
                    </div>
                  </div>
                  <div style={{ background: '#1f2937', padding: '0.5rem', borderRadius: '4px' }}>
                    <div style={{ fontSize: '0.7rem', color: '#94a3b8' }}>Dot Ball %</div>
                    <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#f1f5f9' }}>
                      {result.matchup_stats.dot_ball_pct !== null && result.matchup_stats.dot_ball_pct !== undefined
                        ? `${result.matchup_stats.dot_ball_pct}%`
                        : 'N/A'}
                    </div>
                  </div>
                </div>
                {result.matchup_stats.data_coverage_note && (
                  <p style={{ margin: 0, fontSize: '0.75rem', color: '#94a3b8', fontStyle: 'italic' }}>
                    {result.matchup_stats.data_coverage_note}
                  </p>
                )}
                {result.bowler_provenance?.bowler_type && (
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '0.5rem', paddingTop: '0.5rem', borderTop: '1px solid #1f2937', fontSize: '0.75rem' }}>
                    <span style={{ color: '#94a3b8' }}>Bowler Discipline Source:</span>
                    <span style={{ fontWeight: 600, color: result.bowler_provenance.bowler_type === 'curated_categorical' ? '#34d399' : '#fbbf24' }}>
                      {result.bowler_provenance.bowler_type}
                    </span>
                  </div>
                )}
                <div style={{ marginTop: '0.6rem', fontSize: '0.7rem', color: '#64748b', lineHeight: 1.35 }}>
                  Direction is inherited from source wagon-wheel sectors (1–8). Distance bands are categorical proxies from runs, not measured coordinates. Deliveries with Zone 0 (spatial data unavailable) are strictly excluded from spatial danger calculations.
                </div>
              </div>

              {/* Model Confidence Disclosure Card */}
              {result.model_confidence && (
                <div
                  id="model-confidence-card"
                  style={{ background: '#111827', padding: '1rem', borderRadius: '6px', border: '1px solid #1f2937' }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                    <span style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: '#94a3b8', letterSpacing: '0.05em' }}>
                      Model Confidence Disclosure
                    </span>
                    <span
                      style={{
                        fontSize: '0.75rem',
                        fontWeight: 600,
                        color: '#f59e0b',
                        background: '#d9770622',
                        padding: '0.2rem 0.5rem',
                        borderRadius: '4px',
                        border: '1px solid #d97706',
                      }}
                    >
                      {result.model_confidence.status}
                    </span>
                  </div>
                  <div
                    style={{
                      display: 'grid',
                      gridTemplateColumns: '1fr 1fr',
                      gap: '0.5rem',
                      textAlign: 'center',
                      margin: '0.75rem 0',
                    }}
                  >
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

              {/* Optimization Scores */}
              <div style={{ background: '#111827', padding: '1rem', borderRadius: '6px', border: '1px solid #1f2937' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                  <span style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: '#94a3b8', letterSpacing: '0.05em' }}>
                    Optimization Scores {evaluation && !evaluationStale && '(What-If Evaluated)'}
                  </span>
                  {anyPlacementsModified && (
                    <span style={{ fontSize: '0.7rem', color: '#38bdf8', background: '#0284c722', padding: '0.15rem 0.4rem', borderRadius: '3px' }}>
                      Modified Configuration
                    </span>
                  )}
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0.5rem', textAlign: 'center' }}>
                  <div style={{ background: '#1f2937', padding: '0.5rem', borderRadius: '4px' }}>
                    <div style={{ fontSize: '0.7rem', color: '#94a3b8' }}>ERS (Runs Saved)</div>
                    <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#38bdf8' }}>
                      {(evaluation ? evaluation.ers : result.ers).toFixed(2)}
                    </div>
                  </div>
                  <div style={{ background: '#1f2937', padding: '0.5rem', borderRadius: '4px' }}>
                    <div style={{ fontSize: '0.7rem', color: '#94a3b8' }}>EWO (Wicket Opp)</div>
                    <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#34d399' }}>
                      {(evaluation ? evaluation.ewo : result.ewo).toFixed(2)}
                    </div>
                  </div>
                  <div style={{ background: '#1f2937', padding: '0.5rem', borderRadius: '4px' }}>
                    <div style={{ fontSize: '0.7rem', color: '#94a3b8' }}>CDS (Coverage)</div>
                    <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#a78bfa' }}>
                      {(evaluation ? evaluation.cds : result.cds).toFixed(2)}
                    </div>
                  </div>
                </div>
              </div>

              {/* Active Fielder Inspector Card */}
              {selectedPlacement && (
                <div
                  id="active-fielder-inspector"
                  style={{
                    background: '#111827',
                    padding: '1rem',
                    borderRadius: '6px',
                    border: '1px solid #38bdf844',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem' }}>
                    <span style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: '#38bdf8', fontWeight: 600 }}>
                      Selected Fielder #{selectedFielderIndex! + 1}
                    </span>
                    <span
                      style={{
                        fontSize: '0.75rem',
                        padding: '0.15rem 0.4rem',
                        borderRadius: '3px',
                        background: isPlacementModified(selectedFielderIndex!) ? '#b45309' : '#047857',
                        color: '#ffffff',
                      }}
                    >
                      {isPlacementModified(selectedFielderIndex!) ? 'Human-Modified' : 'Server Recommendation'}
                    </span>
                  </div>
                  <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#f1f5f9' }}>
                    Position: {selectedPlacement.position_name}
                  </div>
                  <div style={{ fontSize: '0.85rem', color: '#94a3b8', marginBottom: '0.5rem' }}>
                    Player: <strong style={{ color: '#e2e8f0' }}>{selectedPlacement.fielder?.name || 'Unassigned'}</strong> · Role:{' '}
                    <span style={{ textTransform: 'capitalize', color: '#38bdf8' }}>{selectedPlacement.role}</span>
                  </div>
                  <div style={{ fontSize: '0.8rem', color: '#cbd5e1', lineHeight: 1.4 }}>
                    <em>"{selectedPlacement.reason || 'Strategic fielding position'}"</em>
                  </div>
                  <div style={{ marginTop: '0.6rem', fontSize: '0.75rem', color: '#64748b', fontFamily: 'monospace' }}>
                    Coords: X = {selectedPlacement.x.toFixed(1)}m, Y = {selectedPlacement.y.toFixed(1)}m
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Unified 11 Recommended Field Placements & Human-in-the-Loop What-If Evaluation */}
          <div
            id="what-if-panel"
            style={{
              background: '#111827',
              borderRadius: '8px',
              border: '1px solid #1f2937',
              overflow: 'hidden',
            }}
          >
            {/* Header & Evaluation Actions */}
            <div
              style={{
                padding: '0.85rem 1.25rem',
                borderBottom: '1px solid #1f2937',
                background: '#1e293b',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                flexWrap: 'wrap',
                gap: '1rem',
              }}
            >
              <div>
                <span style={{ fontWeight: 600, fontSize: '1rem', color: '#f1f5f9' }}>
                  11 Recommended Field Placements
                </span>
                <span style={{ fontSize: '0.8rem', color: '#94a3b8', marginLeft: '0.75rem' }}>
                  (Interactive What-If Evaluation & Coordinate Tuning)
                </span>
              </div>

              <div style={{ display: 'flex', gap: '0.6rem', alignItems: 'center' }}>
                <button
                  type="button"
                  id="reset-recommendation-btn"
                  onClick={handleResetToRecommendation}
                  disabled={!anyPlacementsModified}
                  style={{
                    padding: '0.5rem 0.85rem',
                    background: anyPlacementsModified ? '#334155' : '#1e293b',
                    color: anyPlacementsModified ? '#f1f5f9' : '#64748b',
                    border: '1px solid #475569',
                    borderRadius: '4px',
                    fontSize: '0.8rem',
                    fontWeight: 600,
                    cursor: anyPlacementsModified ? 'pointer' : 'not-allowed',
                  }}
                >
                  ↺ Reset to recommendation
                </button>

                <button
                  type="button"
                  id="evaluate-field-btn"
                  onClick={evaluateEditedField}
                  disabled={evaluationLoading || editedPlacements.some((p) => !p.fielder)}
                  style={{
                    padding: '0.5rem 1rem',
                    background:
                      evaluationLoading || editedPlacements.some((p) => !p.fielder) ? '#475569' : '#7c3aed',
                    color: '#ffffff',
                    border: 'none',
                    borderRadius: '4px',
                    fontSize: '0.8rem',
                    fontWeight: 600,
                    cursor:
                      evaluationLoading || editedPlacements.some((p) => !p.fielder) ? 'not-allowed' : 'pointer',
                  }}
                >
                  {evaluationLoading ? 'Evaluating...' : 'Evaluate edited field'}
                </button>
              </div>
            </div>

            {/* Stale Warning / Status Alert */}
            {evaluationStale && (
              <div
                role="status"
                style={{
                  background: '#78350f',
                  borderBottom: '1px solid #d97706',
                  color: '#fef3c7',
                  padding: '0.6rem 1.25rem',
                  fontSize: '0.82rem',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                }}
              >
                <span>⚠</span>
                <span>
                  <strong>Stale Evaluation:</strong> Field coordinates were modified since the last server evaluation. Click
                  <strong>"Evaluate edited field"</strong> to recalculate legality and scores with server engines.
                </span>
              </div>
            )}

            {evaluationError && (
              <div
                role="alert"
                style={{
                  background: '#7f1d1d',
                  borderBottom: '1px solid #ef4444',
                  color: '#fecaca',
                  padding: '0.6rem 1.25rem',
                  fontSize: '0.82rem',
                }}
              >
                <strong>Evaluation Warning:</strong> {evaluationError}
              </div>
            )}

            {/* Evaluated Outcome Feedback Strip */}
            {evaluation && !evaluationStale && (
              <div
                style={{
                  background: evaluation.is_legal ? '#064e3b44' : '#7f1d1d44',
                  borderBottom: '1px solid #1f2937',
                  padding: '0.65rem 1.25rem',
                  fontSize: '0.85rem',
                  color: evaluation.is_legal ? '#6ee7b7' : '#fecaca',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}
              >
                <span>
                  <strong>{evaluation.is_legal ? '✓ Server verified: Legal field' : '⚠ Server reported restrictions'}:</strong>{' '}
                  ERS {evaluation.ers.toFixed(2)} · EWO {evaluation.ewo.toFixed(2)} · CDS {evaluation.cds.toFixed(2)}
                  {evaluation.violations.length > 0 && ` (${evaluation.violations.join('; ')})`}
                </span>
                <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                  Coverage: {evaluation.data_coverage || 'custom'}
                </span>
              </div>
            )}

            {/* Placements Table */}
            <div style={{ overflowX: 'auto' }}>
              <table
                aria-label="Field Placements Table"
                style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem', textAlign: 'left' }}
              >
                <thead>
                  <tr style={{ background: '#0f172a', color: '#94a3b8', borderBottom: '1px solid #1f2937' }}>
                    <th style={{ padding: '0.6rem 0.8rem' }}>#</th>
                    <th style={{ padding: '0.6rem 0.8rem' }}>Position Name</th>
                    <th style={{ padding: '0.6rem 0.8rem' }}>Player</th>
                    <th style={{ padding: '0.6rem 0.8rem' }}>X (m)</th>
                    <th style={{ padding: '0.6rem 0.8rem' }}>Y (m)</th>
                    <th style={{ padding: '0.6rem 0.8rem' }}>Role</th>
                    <th style={{ padding: '0.6rem 0.8rem' }}>Status</th>
                    <th style={{ padding: '0.6rem 0.8rem' }}>Tactical Reason</th>
                  </tr>
                </thead>
                <tbody>
                  {editedPlacements.map((p, idx) => {
                    const isSelected = selectedFielderIndex === idx;
                    const isModified = isPlacementModified(idx);

                    return (
                      <tr
                        key={`${p.position_name}-${idx}`}
                        onClick={() => setSelectedFielderIndex(idx)}
                        style={{
                          borderBottom: '1px solid #1f2937',
                          background: isSelected ? '#1e3a5f' : idx % 2 === 0 ? '#111827' : '#131d2e',
                          cursor: 'pointer',
                          transition: 'background 0.15s ease',
                        }}
                      >
                        <td style={{ padding: '0.6rem 0.8rem', color: isSelected ? '#38bdf8' : '#64748b' }}>
                          {idx + 1}
                        </td>
                        <td style={{ padding: '0.6rem 0.8rem', fontWeight: 600, color: '#38bdf8' }}>
                          {p.position_name}
                        </td>
                        <td style={{ padding: '0.6rem 0.8rem', color: '#e2e8f0' }}>
                          {p.fielder?.name || 'Unassigned'}
                        </td>
                        <td style={{ padding: '0.4rem 0.8rem' }}>
                          <input
                            aria-label={`${p.position_name} X`}
                            type="number"
                            step="0.1"
                            value={p.x}
                            onChange={(e) => updatePlacementCoordinate(idx, 'x', e.target.value)}
                            onClick={(e) => e.stopPropagation()}
                            style={{
                              width: '5.5rem',
                              padding: '0.3rem',
                              background: '#0f172a',
                              color: isModified ? '#facc15' : '#f1f5f9',
                              border: isModified ? '1px solid #eab308' : '1px solid #374151',
                              borderRadius: '4px',
                              fontFamily: 'monospace',
                            }}
                          />
                        </td>
                        <td style={{ padding: '0.4rem 0.8rem' }}>
                          <input
                            aria-label={`${p.position_name} Y`}
                            type="number"
                            step="0.1"
                            value={p.y}
                            onChange={(e) => updatePlacementCoordinate(idx, 'y', e.target.value)}
                            onClick={(e) => e.stopPropagation()}
                            style={{
                              width: '5.5rem',
                              padding: '0.3rem',
                              background: '#0f172a',
                              color: isModified ? '#facc15' : '#f1f5f9',
                              border: isModified ? '1px solid #eab308' : '1px solid #374151',
                              borderRadius: '4px',
                              fontFamily: 'monospace',
                            }}
                          />
                        </td>
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
                        <td style={{ padding: '0.6rem 0.8rem' }}>
                          <span
                            style={{
                              padding: '0.15rem 0.4rem',
                              borderRadius: '3px',
                              fontSize: '0.7rem',
                              background: isModified ? '#78350f' : '#14532d',
                              color: isModified ? '#fef08a' : '#bbf7d0',
                              border: isModified ? '1px solid #ca8a04' : '1px solid #16a34a',
                            }}
                          >
                            {isModified ? 'Human-Modified' : 'Server Recommendation'}
                          </span>
                        </td>
                        <td style={{ padding: '0.6rem 0.8rem', color: '#cbd5e1' }}>
                          {p.reason || 'Tactical positioning'}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </section>
      )}

      {/* Main Mode 2: Live Ball-by-Ball Engine */}
      {activeTab === 'live' && (
        <section aria-label="Live Delivery Engine" style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {tacticalAdjustment && (
            <div
              style={{
                background: '#0c4a6e',
                border: '1px solid #0284c7',
                color: '#e0f2fe',
                padding: '0.85rem 1.25rem',
                borderRadius: '6px',
                fontSize: '0.9rem',
              }}
            >
              <strong>⚡ Dynamic Tactical Adjustment:</strong> {tacticalAdjustment}
            </div>
          )}

          <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1.8fr', gap: '1.5rem', alignItems: 'start' }}>
            <LiveDeliveryConsole
              batterName={batterName}
              bowlerName={bowlerName}
              matchFormat={matchFormat}
              over={over}
              ball={ball}
              runs={runs}
              wickets={wickets}
              tacticalObjective={tacticalObjective}
              venueId={groundPresetId}
              onDeliveryLogged={handleLiveDeliveryLogged}
              onUndo={handleLiveUndo}
              onReset={handleLiveReset}
              deliveryHistory={deliveryHistory}
              liveCommentary={liveCommentary}
              phase={getPhaseName(over, matchFormat).toUpperCase()}
            />

            {/* Live 3D Field Spatial Representation */}
            <div
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
                fielders={editedPlacements.length > 0 ? editedPlacements : (result?.placements || [])}
                zoneChart={result?.zone_chart}
                venueId={groundPresetId}
                pitchType="standard"
                selectedFielderIndex={selectedFielderIndex}
                onSelectFielder={(idx) => setSelectedFielderIndex(idx)}
              />
            </div>
          </div>
        </section>
      )}

      {/* Main Mode 3: Multi-Over Strategic Gameplan */}
      {activeTab === 'gameplan' && (
        <section aria-label="Multi-Over Gameplan" style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {/* Gameplan Request Controls */}
          <div
            style={{
              background: '#111827',
              padding: '1rem 1.25rem',
              borderRadius: '8px',
              border: '1px solid #1f2937',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              flexWrap: 'wrap',
              gap: '1rem',
            }}
          >
            <div>
              <span style={{ fontWeight: 600, fontSize: '1rem', color: '#38bdf8' }}>
                Multi-Over Strategic Bowling & Fielding Plan
              </span>
              <p style={{ margin: '0.2rem 0 0 0', fontSize: '0.8rem', color: '#94a3b8' }}>
                Simulate match-phase transitions, recommended delivery lengths/channels, and boundary defenses
              </p>
            </div>

            <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
              <div>
                <label style={{ fontSize: '0.75rem', color: '#94a3b8', marginRight: '0.5rem' }}>
                  Planned Overs:
                </label>
                <select
                  value={plannedOvers}
                  onChange={(e) => setPlannedOvers(Number(e.target.value))}
                  style={{
                    padding: '0.4rem',
                    background: '#1f2937',
                    color: '#f1f5f9',
                    border: '1px solid #374151',
                    borderRadius: '4px',
                  }}
                >
                  {[3, 4, 5, 6, 8, 10].map((n) => (
                    <option key={n} value={n}>
                      {n} Overs
                    </option>
                  ))}
                </select>
              </div>

              <button
                type="button"
                onClick={handleGenerateGameplan}
                disabled={gameplanLoading}
                style={{
                  padding: '0.55rem 1.2rem',
                  background: gameplanLoading ? '#475569' : '#0284c7',
                  color: '#ffffff',
                  border: 'none',
                  borderRadius: '4px',
                  fontWeight: 600,
                  fontSize: '0.85rem',
                  cursor: gameplanLoading ? 'not-allowed' : 'pointer',
                }}
              >
                {gameplanLoading ? 'Generating Gameplan...' : 'Generate Multi-Over Gameplan'}
              </button>
            </div>
          </div>

          {gameplanSequence.length > 0 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
              <GameplanTimeline
                sequence={gameplanSequence}
                activeOverIndex={activeGameplanOverIndex}
                onSelectOver={(idx) => {
                  setActiveGameplanOverIndex(idx);
                  if (gameplanSequence[idx].placements) {
                    setEditedPlacements(gameplanSequence[idx].placements);
                  }
                }}
                groundName={groundPresets.find((g) => g.id === groundPresetId)?.name}
              />

              <div
                style={{
                  position: 'relative',
                  height: '520px',
                  background: '#04070e',
                  borderRadius: '8px',
                  border: '1px solid #1e293b',
                  overflow: 'hidden',
                }}
              >
                <ThreeField
                  fielders={editedPlacements}
                  venueId={groundPresetId}
                  pitchType="standard"
                  selectedFielderIndex={selectedFielderIndex}
                  onSelectFielder={(idx) => setSelectedFielderIndex(idx)}
                />
              </div>
            </div>
          )}
        </section>
      )}

      {/* Dataset Studio & Lineage Modal */}
      <DatasetStudioModal
        isOpen={datasetModalOpen}
        onClose={() => setDatasetModalOpen(false)}
        onDatasetUpdated={() => {
          fetch('/api/v1/players')
            .then((res) => (res.ok ? res.json() : null))
            .then((data) => {
              if (data?.batters) setAvailableBatters(data.batters);
              if (data?.bowlers) setAvailableBowlers(data.bowlers);
            });
        }}
      />
    </div>
  );
};
