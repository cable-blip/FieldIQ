import { useState } from 'react';
import { MatchContextPanel, MatchState } from './components/MatchContextPanel';
import { TacticalPanel, FielderPosition } from './components/TacticalPanel';
import { ThreeField } from './components/ThreeField';
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

  // Drag handler updating positions in real-time
  const handleUpdateFielder = (name: string, x: number, y: number) => {
    setFielders((prev) =>
      prev.map((f) => (f.name === name ? { ...f, x, y } : f))
    );
  };

  const handleResetPositions = () => {
    setFielders(DEFAULT_FIELDERS);
  };

  const handleMatchSubmit = async (matchState: MatchState) => {
    setLoading(true);
    setError(null);
    setObjective(matchState.tactical_objective);

    try {
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

      // Read response schemas to verify API integration
      await response.json();
    } catch (err: any) {
      setError(err.message || 'Failed to fetch tactical analysis.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-layout">
      <header className="app-header">
        <h1>FieldIQ — Interactive 3D Tactical Field Optimizer</h1>
      </header>

      {error && (
        <div className="app-error-banner">
          ⚠️ <strong>API Connection Error:</strong> {error} (Displaying local fallback metrics)
        </div>
      )}

      <main className="app-main">
        <div className="app-grid">
          {/* Left Sidebar: Match Context */}
          <div className="grid-sidebar-left">
            <MatchContextPanel onSubmit={handleMatchSubmit} loading={loading} />
          </div>

          {/* Center Column: 3D Field Canvas */}
          <div className="grid-center">
            <ThreeField fielders={fielders} onUpdateFielder={handleUpdateFielder} />
            <div className="instruction-footer">
              🖱️ <strong>Navigation:</strong> Drag with Left Click to Rotate | Right Click to Pan | Scroll to Zoom. <br />
              🏃 <strong>Field Optimization:</strong> Click and drag any player marker (sphere) directly on the field.
            </div>
          </div>

          {/* Right Sidebar: Tactical Scores */}
          <div className="grid-sidebar-right">
            <TacticalPanel
              fielders={fielders}
              onReset={handleResetPositions}
              objective={objective}
            />
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;
