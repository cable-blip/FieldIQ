import { useState } from 'react';
import { MatchContextPanel } from './components/MatchContextPanel';
import type { MatchState } from './components/MatchContextPanel';
import { TacticalPanel } from './components/TacticalPanel';
import type { FielderPosition, AlternativeField } from './components/TacticalPanel';
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
  const [metrics, setMetrics] = useState<any>(null);
  const [alternatives, setAlternatives] = useState<AlternativeField[]>([]);
  const [selectedStrategy, setSelectedStrategy] = useState<string>('balanced');

  // Drag handler updating positions in real-time
  const handleUpdateFielder = (name: string, x: number, y: number) => {
    setFielders((prev) =>
      prev.map((f) => (f.name === name ? { ...f, x, y } : f))
    );
  };

  const handleResetPositions = () => {
    setFielders(DEFAULT_FIELDERS);
    setMetrics(null);
    setAlternatives([]);
    setSelectedStrategy('balanced');
  };

  const handleSelectStrategy = (strategyId: string) => {
    setSelectedStrategy(strategyId);
    const target = alternatives.find((a) => a.strategy_id === strategyId);
    if (target) {
      if (target.placements && target.placements.length > 0) {
        const mappedFielders = target.placements.map((p: any) => ({
          name: p.position_name,
          x: p.x,
          y: p.y,
          role: p.role,
        }));
        setFielders(mappedFielders);
      }
      setMetrics((prev: any) => ({
        ...prev,
        ers: target.ers,
        ewo: target.ewo,
        cds: target.cds,
      }));
    }
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

      const data = await response.json();
      
      if (data.placements && data.placements.length > 0) {
        const mappedFielders = data.placements.map((p: any) => ({
          name: p.position_name,
          x: p.x,
          y: p.y,
          role: p.role,
        }));
        setFielders(mappedFielders);
      }

      setMetrics({
        ers: data.ers,
        ewo: data.ewo,
        cds: data.cds,
        explanations: data.tactical_explanations,
        is_legal: data.is_legal,
        violations: data.violations,
        matchup_stats: data.matchup_stats,
      });

      if (data.alternative_fields && data.alternative_fields.length > 0) {
        const mappedAlts: AlternativeField[] = data.alternative_fields.map((alt: any) => ({
          strategy_id: alt.strategy_id,
          strategy_name: alt.strategy_name,
          description: alt.description,
          placements: alt.placements.map((p: any) => ({
            name: p.position_name,
            x: p.x,
            y: p.y,
            role: p.role,
          })),
          ers: alt.ers,
          ewo: alt.ewo,
          cds: alt.cds,
        }));
        setAlternatives(mappedAlts);
        setSelectedStrategy('balanced');
      }

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
        <aside className="sidebar-left">
          <MatchContextPanel onSubmit={handleMatchSubmit} loading={loading} />
        </aside>

        <section className="center-viewport">
          <ThreeField fielders={fielders} onUpdateFielder={handleUpdateFielder} />
        </section>

        <aside className="sidebar-right">
          <TacticalPanel
            fielders={fielders}
            onReset={handleResetPositions}
            objective={objective}
            metrics={metrics}
            alternatives={alternatives}
            selectedStrategy={selectedStrategy}
            onSelectStrategy={handleSelectStrategy}
          />
        </aside>
      </main>
    </div>
  );
}

export default App;
