import React, { useState, useEffect } from 'react';
import './MatchContextPanel.css';

export interface MatchState {
  match_format: 'ODI' | 'T20' | 'TEST';
  innings: number;
  over: number;
  runs: number;
  wickets: number;
  batter_name: string;
  bowler_name: string;
  tactical_objective: 'attack_wicket' | 'prevent_boundary' | 'build_pressure' | 'stop_singles';
}

interface MatchContextPanelProps {
  onSubmit: (state: MatchState) => void;
  loading: boolean;
}

export const MatchContextPanel: React.FC<MatchContextPanelProps> = ({ onSubmit, loading }) => {
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

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({
      match_format: format,
      innings,
      over,
      runs,
      wickets,
      batter_name: batterName,
      bowler_name: bowlerName,
      tactical_objective: objective,
    });
  };

  const objectivesList: { id: 'attack_wicket' | 'prevent_boundary' | 'build_pressure' | 'stop_singles'; label: string; icon: string; desc: string }[] = [
    { id: 'attack_wicket', label: 'Attack Wicket', icon: '🎯', desc: 'Packs close catchers & slip cordon' },
    { id: 'prevent_boundary', label: 'Prevent Boundary', icon: '🛡️', desc: 'Deploys maximum deep boundary riders' },
    { id: 'build_pressure', label: 'Build Pressure', icon: '⏳', desc: 'Restricts strike rotation & spikes dots' },
    { id: 'stop_singles', label: 'Stop Singles', icon: '🛑', desc: 'Tightens inner circle ring' },
  ];

  return (
    <div className="match-context-panel">
      <div className="panel-header">
        <span className="header-icon">🎮</span>
        <div className="header-title-wrap">
          <h3>TACTICAL CONTROL</h3>
          <span className="header-subtitle font-mono">SCENARIO CONFIGURATION</span>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="context-form">
        {/* Match Format Segmented Pills */}
        <div className="form-group">
          <label className="field-label">Match Format</label>
          <div className="format-pills">
            <button
              type="button"
              className={`pill-btn ${format === 'ODI' ? 'active' : ''}`}
              onClick={() => {
                setFormat('ODI');
              }}
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

        {/* Submit Action Button */}
        <button
          type="submit"
          disabled={loading}
          className="btn-submit-glow"
        >
          {loading ? '⚡ RUNNING MONTE CARLO SIMS...' : '⚡ RECOMMEND TACTICAL FIELD'}
        </button>
      </form>
    </div>
  );
};
