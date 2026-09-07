import React, { useState, useEffect } from 'react';
import './MatchContextPanel.css';

export interface EnvironmentalConditionsState {
  pitch_type: 'standard' | 'green_seam' | 'dusty_spin' | 'flat_highway' | 'slow_low';
  pitch_wear_index?: number;
  wind_speed_kph?: number;
  wind_angle_degrees?: number;
  humidity_pct?: number;
  dew_index?: number;
}

export interface MatchState {
  match_format: 'ODI' | 'T20' | 'TEST';
  innings: number;
  over: number;
  runs: number;
  wickets: number;
  batter_name: string;
  bowler_name: string;
  tactical_objective: 'attack_wicket' | 'prevent_boundary' | 'build_pressure' | 'stop_singles';
  ground_preset_id?: string;
  environmental_conditions?: EnvironmentalConditionsState;
  is_gameplan_mode?: boolean;
  planned_overs?: number;
}

interface MatchContextPanelProps {
  onSubmit: (state: MatchState) => void;
  loading: boolean;
  onVenueChange?: (presetId: string) => void;
  onPitchTypeChange?: (pitchType: string) => void;
}

export const VENUE_PRESETS = [
  { id: 'lords', name: "Lord's (London)", pitch: 'green_seam' as const, desc: 'Sloped, 60m square / 76m straight' },
  { id: 'mcg', name: 'MCG (Melbourne)', pitch: 'flat_highway' as const, desc: 'Massive, 82m straight / 74m square' },
  { id: 'wankhede', name: 'Wankhede (Mumbai)', pitch: 'standard' as const, desc: 'True bounce, compact 60m-62m' },
  { id: 'eden_park', name: 'Eden Park (Auckland)', pitch: 'standard' as const, desc: 'Postage stamp, 55m straight' },
  { id: 'adelaide', name: 'Adelaide Oval', pitch: 'standard' as const, desc: 'Long 80m straight / 58m square' },
  { id: 'chepauk', name: 'Chepauk (Chennai)', pitch: 'dusty_spin' as const, desc: 'Abrasive turning track' },
  { id: 'standard', name: 'Standard ICC Oval', pitch: 'standard' as const, desc: 'Uniform 65m boundary' },
];

export const PITCH_TYPES = [
  { id: 'standard' as const, label: 'Standard', icon: '🏏', desc: 'Neutral true bounce' },
  { id: 'green_seam' as const, label: 'Green Seam', icon: '🌱', desc: 'Seam +35%, Slip Carry 1.4x' },
  { id: 'dusty_spin' as const, label: 'Dusty Spin', icon: '🌪️', desc: 'Spin +45%, Bat-Pad Traps' },
  { id: 'flat_highway' as const, label: 'Flat Highway', icon: '🛣️', desc: 'Velocity +12%, Belter' },
  { id: 'slow_low' as const, label: 'Slow & Low', icon: '🧱', desc: 'Low bounce, Miscue traps' },
];

export const MatchContextPanel: React.FC<MatchContextPanelProps> = ({
  onSubmit,
  loading,
  onVenueChange,
  onPitchTypeChange
}) => {
  const [format, setFormat] = useState<'ODI' | 'T20' | 'TEST'>('ODI');
  const [innings, setInnings] = useState<number>(1);
  const [over, setOver] = useState<number>(4);
  const [runs, setRuns] = useState<number>(18);
  const [wickets, setWickets] = useState<number>(0);
  
  const [batters, setBatters] = useState<string[]>([
    'Virat Kohli', 'Rohit Sharma', 'Babar Azam', 'AB de Villiers',
    'Steve Smith', 'David Warner', 'Joe Root', 'Kane Williamson', 'Rishabh Pant'
  ]);
  const [bowlers, setBowlers] = useState<string[]>([
    'Generic Right-Arm Fast (New Ball)', 'Generic Right-Arm Fast (Death)',
    'Short-Ball Enforcer', 'Left-Arm Fast', 'Off-Spinner', 'Leg-Spinner',
    'Left-Arm Orthodox', 'Right-Arm Medium'
  ]);
  
  const [batterName, setBatterName] = useState<string>('Virat Kohli');
  const [bowlerName, setBowlerName] = useState<string>('Generic Right-Arm Fast (New Ball)');
  const [objective, setObjective] = useState<'attack_wicket' | 'prevent_boundary' | 'build_pressure' | 'stop_singles'>('attack_wicket');

  // Modern Environmental & Venue Controls
  const [activeTab, setActiveTab] = useState<'match' | 'environment'>('match');
  const [venueId, setVenueId] = useState<string>('lords');
  const [pitchType, setPitchType] = useState<'standard' | 'green_seam' | 'dusty_spin' | 'flat_highway' | 'slow_low'>('green_seam');
  const [windSpeed, setWindSpeed] = useState<number>(18);
  const [windAngle, setWindAngle] = useState<number>(45);
  const [humidity, setHumidity] = useState<number>(65);
  const [dewIndex, setDewIndex] = useState<number>(0.1);
  const [isGameplanMode, setIsGameplanMode] = useState<boolean>(false);
  const [plannedOvers, setPlannedOvers] = useState<number>(4);

  useEffect(() => {
    let active = true;
    const fetchPlayers = async () => {
      try {
        const response = await fetch('/api/v1/players');
        if (response.ok) {
          const data = await response.json();
          if (active) {
            if (data.batters && data.batters.length > 0) {
              setBatters(data.batters);
              setBatterName((prev) => data.batters.includes(prev) ? prev : data.batters[0]);
            }
            if (data.bowlers && data.bowlers.length > 0) {
              setBowlers(data.bowlers);
              setBowlerName((prev) => data.bowlers.includes(prev) ? prev : data.bowlers[0]);
            }
          }
        }
      } catch (err) {
        console.error('Failed to fetch player lists from API', err);
      }
    };

    fetchPlayers();
    return () => {
      active = false;
    };
  }, []);

  const handleVenueSelect = (id: string) => {
    setVenueId(id);
    const preset = VENUE_PRESETS.find((v) => v.id === id);
    if (preset) {
      setPitchType(preset.pitch);
      if (onPitchTypeChange) onPitchTypeChange(preset.pitch);
    }
    if (onVenueChange) onVenueChange(id);
  };

  const handlePitchSelect = (type: 'standard' | 'green_seam' | 'dusty_spin' | 'flat_highway' | 'slow_low') => {
    setPitchType(type);
    if (onPitchTypeChange) onPitchTypeChange(type);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const payload: MatchState = {
      match_format: format,
      innings,
      over,
      runs,
      wickets,
      batter_name: batterName,
      bowler_name: bowlerName,
      tactical_objective: objective,
    };

    if (isGameplanMode) {
      payload.is_gameplan_mode = true;
      payload.planned_overs = plannedOvers;
    }

    if (activeTab === 'environment') {
      payload.ground_preset_id = venueId;
      payload.environmental_conditions = {
        pitch_type: pitchType,
        wind_speed_kph: windSpeed,
        wind_angle_degrees: windAngle,
        humidity_pct: humidity,
        dew_index: dewIndex
      };
    }

    onSubmit(payload);
  };

  const objectivesList: { id: 'attack_wicket' | 'prevent_boundary' | 'build_pressure' | 'stop_singles'; label: string; icon: string; desc: string }[] = [
    { id: 'attack_wicket', label: 'Attack Wicket', icon: '🎯', desc: 'Packs close catchers & slip cordon' },
    { id: 'prevent_boundary', label: 'Prevent Boundary', icon: '🛡️', desc: 'Deploys maximum deep boundary riders' },
    { id: 'build_pressure', label: 'Build Pressure', icon: '⏳', desc: 'Restricts strike rotation & spikes dots' },
    { id: 'stop_singles', label: 'Stop Singles', icon: '🛑', desc: 'Tightens inner circle ring' },
  ];

  return (
    <div className="match-context-panel">
      {/* High-Tech Cockpit Header */}
      <div className="panel-header">
        <span className="header-icon">🕹️</span>
        <div className="header-title-wrap">
          <h3 className="font-display">TACTICAL CONTROL</h3>
          <span className="header-subtitle font-mono">NEURAL SCENARIO COCKPIT</span>
        </div>
      </div>

      {/* Modern Tab Selector: Scenario vs Environmental Aerodynamics */}
      <div className="panel-subtabs">
        <button
          type="button"
          className={`subtab-btn ${activeTab === 'match' ? 'active' : ''}`}
          onClick={() => setActiveTab('match')}
        >
          Matchup & Score
        </button>
        <button
          type="button"
          className={`subtab-btn ${activeTab === 'environment' ? 'active' : ''}`}
          onClick={() => setActiveTab('environment')}
        >
          Pitch & Venue 🏟️
        </button>
      </div>

      <form onSubmit={handleSubmit} className="context-form">
        {activeTab === 'match' ? (
          <>
            {/* Match Format Segmented Pills */}
            <div className="form-group">
              <label className="field-label">Match Format</label>
              <div className="format-pills">
                <button
                  type="button"
                  className={`pill-btn ${format === 'ODI' ? 'active' : ''}`}
                  onClick={() => setFormat('ODI')}
                >
                  ODI (50 Overs)
                </button>
                <button
                  type="button"
                  className={`pill-btn ${format === 'T20' ? 'active' : ''}`}
                  onClick={() => {
                    setFormat('T20');
                    if (over > 20) setOver(20);
                  }}
                >
                  T20 (20 Overs)
                </button>
              </div>
            </div>

            {/* Live Match State Grid */}
            <div className="form-row-grid">
              <div className="form-group">
                <label className="field-label" htmlFor="innings-select">Innings</label>
                <select
                  id="innings-select"
                  value={innings}
                  onChange={(e) => setInnings(parseInt(e.target.value))}
                  className="input-select font-mono"
                >
                  <option value={1}>1st Innings</option>
                  <option value={2}>2nd Innings</option>
                </select>
              </div>
              <div className="form-group">
                <label className="field-label" htmlFor="over-input">Over</label>
                <input
                  id="over-input"
                  type="number"
                  min={1}
                  max={format === 'T20' ? 20 : 50}
                  value={over}
                  onChange={(e) => setOver(parseInt(e.target.value) || 1)}
                  className="input-text font-mono"
                />
              </div>
              <div className="form-group">
                <label className="field-label" htmlFor="runs-input">Runs</label>
                <input
                  id="runs-input"
                  type="number"
                  min={0}
                  value={runs}
                  onChange={(e) => setRuns(parseInt(e.target.value) || 0)}
                  className="input-text font-mono"
                />
              </div>
              <div className="form-group">
                <label className="field-label" htmlFor="wickets-input">Wickets</label>
                <input
                  id="wickets-input"
                  type="number"
                  min={0}
                  max={10}
                  value={wickets}
                  onChange={(e) => setWickets(parseInt(e.target.value) || 0)}
                  className="input-text font-mono"
                />
              </div>
            </div>

            {/* Batter Selector */}
            <div className="form-group">
              <div className="label-with-badge">
                <label className="field-label" htmlFor="batter-select">Active Batter</label>
                <span className="profile-badge">RHB Specialist</span>
              </div>
              <select
                id="batter-select"
                value={batterName}
                onChange={(e) => setBatterName(e.target.value)}
                className="input-select"
              >
                {batters.map((b) => (
                  <option key={b} value={b}>
                    {b}
                  </option>
                ))}
              </select>
            </div>

            {/* Bowler Selector */}
            <div className="form-group">
              <div className="label-with-badge">
                <label className="field-label" htmlFor="bowler-select">Active Bowler</label>
                <span className="profile-badge pace">PACE EXPRESS</span>
              </div>
              <select
                id="bowler-select"
                value={bowlerName}
                onChange={(e) => setBowlerName(e.target.value)}
                className="input-select"
              >
                {bowlers.map((b) => (
                  <option key={b} value={b}>
                    {b}
                  </option>
                ))}
              </select>
            </div>

            {/* Tactical Objective Grid */}
            <div className="form-group">
              <label className="field-label">Tactical Objective</label>
              <div className="objectives-grid">
                {objectivesList.map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    className={`objective-card ${objective === item.id ? 'active' : ''}`}
                    onClick={() => setObjective(item.id)}
                  >
                    <span className="obj-icon">{item.icon}</span>
                    <div className="obj-text">
                      <span className="obj-name">{item.label}</span>
                      <span className="obj-desc">{item.desc}</span>
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {/* Multi-Over Strategic Gameplan Toggle */}
            <div className="gameplan-toggle-card">
              <div className="gameplan-toggle-header">
                <div>
                  <span className="gameplan-title font-display">📈 Multi-Over Gameplan</span>
                  <p className="gameplan-sub font-mono">Sequence 3-5 overs with dynamic variations</p>
                </div>
                <button
                  type="button"
                  className={`toggle-switch-btn ${isGameplanMode ? 'active' : ''}`}
                  onClick={() => setIsGameplanMode(!isGameplanMode)}
                >
                  {isGameplanMode ? 'ACTIVE' : 'OFF'}
                </button>
              </div>

              {isGameplanMode && (
                <div className="gameplan-stepper">
                  <span className="field-label">Sequence Length:</span>
                  <div className="stepper-pills">
                    {[3, 4, 5].map((num) => (
                      <button
                        key={num}
                        type="button"
                        className={`stepper-pill ${plannedOvers === num ? 'active' : ''}`}
                        onClick={() => setPlannedOvers(num)}
                      >
                        {num} Overs
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </>
        ) : (
          /* Environmental Aerodynamics & Venue Presets Tab */
          <div className="environment-tab-body">
            {/* Venue Preset Selector */}
            <div className="form-group">
              <label className="field-label">International Ground Geometry</label>
              <select
                value={venueId}
                onChange={(e) => handleVenueSelect(e.target.value)}
                className="input-select font-mono"
              >
                {VENUE_PRESETS.map((v) => (
                  <option key={v.id} value={v.id}>
                    {v.name} · {v.desc}
                  </option>
                ))}
              </select>
            </div>

            {/* Pitch Type Selector Cards */}
            <div className="form-group">
              <label className="field-label">Pitch Surface Physics</label>
              <div className="pitch-cards-grid">
                {PITCH_TYPES.map((p) => (
                  <button
                    key={p.id}
                    type="button"
                    className={`pitch-card ${pitchType === p.id ? 'active' : ''}`}
                    onClick={() => handlePitchSelect(p.id)}
                  >
                    <span className="pitch-icon">{p.icon}</span>
                    <div className="pitch-info">
                      <span className="pitch-label">{p.label}</span>
                      <span className="pitch-desc font-mono">{p.desc}</span>
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {/* Weather & Atmosphere Controls */}
            <div className="form-group">
              <label className="field-label">Atmospheric Aerodynamics</label>
              <div className="weather-sliders-grid">
                <div className="slider-item">
                  <div className="slider-label-row">
                    <span>💨 Wind Speed</span>
                    <span className="slider-val font-mono">{windSpeed} km/h</span>
                  </div>
                  <input
                    type="range"
                    min={0}
                    max={60}
                    value={windSpeed}
                    onChange={(e) => setWindSpeed(parseInt(e.target.value))}
                    className="cyber-slider"
                  />
                </div>

                <div className="slider-item">
                  <div className="slider-label-row">
                    <span>🧭 Wind Direction</span>
                    <span className="slider-val font-mono">{windAngle}°</span>
                  </div>
                  <input
                    type="range"
                    min={0}
                    max={360}
                    step={15}
                    value={windAngle}
                    onChange={(e) => setWindAngle(parseInt(e.target.value))}
                    className="cyber-slider"
                  />
                </div>

                <div className="slider-item">
                  <div className="slider-label-row">
                    <span>💧 Atmospheric Humidity</span>
                    <span className="slider-val font-mono">{humidity}%</span>
                  </div>
                  <input
                    type="range"
                    min={20}
                    max={100}
                    value={humidity}
                    onChange={(e) => setHumidity(parseInt(e.target.value))}
                    className="cyber-slider"
                  />
                </div>

                <div className="slider-item">
                  <div className="slider-label-row">
                    <span>🌙 Evening Dew Friction</span>
                    <span className="slider-val font-mono">{(dewIndex * 100).toFixed(0)}%</span>
                  </div>
                  <input
                    type="range"
                    min={0}
                    max={100}
                    value={dewIndex * 100}
                    onChange={(e) => setDewIndex(parseInt(e.target.value) / 100)}
                    className="cyber-slider"
                  />
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Submit Action Button (Label strictly matches /recommend tactical field/i for vitest tests) */}
        <button
          type="submit"
          disabled={loading}
          className="btn-submit-glow font-display"
        >
          {loading ? '⚡ COMPUTING SIMULATIONS...' : '⚡ RECOMMEND TACTICAL FIELD'}
        </button>
      </form>
    </div>
  );
};
