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
  const [over, setOver] = useState<number>(1);
  const [runs, setRuns] = useState<number>(0);
  const [wickets, setWickets] = useState<number>(0);
  
  const [batters, setBatters] = useState<string[]>(['Virat Kohli', 'AB de Villiers', 'Brendon McCullum', 'David Warner']);
  const [bowlers, setBowlers] = useState<string[]>(['Mitchell Starc', 'Jasprit Bumrah', 'Left-Arm Fast', 'Leg-Spinner']);
  
  const [batterName, setBatterName] = useState<string>('Virat Kohli');
  const [bowlerName, setBowlerName] = useState<string>('Mitchell Starc');
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

  return (
    <div className="match-context-panel">
      <h3>Match Situation Setup</h3>
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="format-select">Match Format</label>
          <select
            id="format-select"
            value={format}
            onChange={(e) => {
              const val = e.target.value as 'ODI' | 'T20' | 'TEST';
              setFormat(val);
              if (val === 'T20' && over > 20) setOver(20);
            }}
            className="input-select"
          >
            <option value="ODI">ODI (50 Overs)</option>
            <option value="T20">T20 (20 Overs)</option>
            <option value="TEST">TEST</option>
          </select>
        </div>

        <div className="form-row">
          <div className="form-group">
            <label htmlFor="innings-select">Innings</label>
            <select
              id="innings-select"
              value={innings}
              onChange={(e) => setInnings(parseInt(e.target.value))}
              className="input-select"
            >
              <option value={1}>1st Innings</option>
              <option value={2}>2nd Innings</option>
            </select>
          </div>
          <div className="form-group">
            <label htmlFor="over-input">Over</label>
            <input
              id="over-input"
              type="number"
              min={1}
              max={format === 'T20' ? 20 : format === 'ODI' ? 50 : 100}
              value={over}
              onChange={(e) => setOver(parseInt(e.target.value) || 1)}
              className="input-text"
            />
          </div>
        </div>

        <div className="form-row">
          <div className="form-group">
            <label htmlFor="runs-input">Runs</label>
            <input
              id="runs-input"
              type="number"
              min={0}
              value={runs}
              onChange={(e) => setRuns(parseInt(e.target.value) || 0)}
              className="input-text"
            />
          </div>
          <div className="form-group">
            <label htmlFor="wickets-input">Wickets</label>
            <input
              id="wickets-input"
              type="number"
              min={0}
              max={10}
              value={wickets}
              onChange={(e) => setWickets(parseInt(e.target.value) || 0)}
              className="input-text"
            />
          </div>
        </div>

        <div className="form-group">
          <label htmlFor="batter-select">Batter Name</label>
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

        <div className="form-group">
          <label htmlFor="bowler-select">Bowler Name</label>
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

        <div className="form-group">
          <label htmlFor="objective-select">Tactical Objective</label>
          <select
            id="objective-select"
            value={objective}
            onChange={(e) => setObjective(e.target.value as any)}
            className="input-select"
          >
            <option value="attack_wicket">Attack Wickets (Wicket focus)</option>
            <option value="prevent_boundary">Prevent Boundaries (Deep protection)</option>
            <option value="build_pressure">Build Pressure (Tight inner ring)</option>
            <option value="stop_singles">Stop Singles (Run containment)</option>
          </select>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="btn btn-primary btn-submit"
        >
          {loading ? 'Optimizing...' : '🎯 Recommend Tactical Field'}
        </button>
      </form>
    </div>
  );
};
