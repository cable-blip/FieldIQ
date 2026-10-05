import React, { useState } from 'react';
import './LiveDeliveryConsole.css';

export interface LoggedDelivery {
  delivery_id: string;
  over: number;
  ball: number;
  display_over: string;
  batter_name: string;
  bowler_name: string;
  runs_batter: number;
  extras: number;
  runs_total: number;
  extra_type: string;
  shot_sector: string;
  shot_band: string;
  is_wicket: boolean;
  wicket_kind: string;
  tactical_adjustment: string;
  timestamp: string;
}

export interface LiveDeliveryConsoleProps {
  batterName: string;
  bowlerName: string;
  matchFormat: string;
  over: number;
  ball: number;
  runs: number;
  wickets: number;
  tacticalObjective: string;
  venueId: string;
  environmentalConditions?: any;
  onDeliveryLogged: (data: any) => void;
  onUndo?: (data: any) => void;
  onReset?: (data: any) => void;
  deliveryHistory?: LoggedDelivery[];
  liveCommentary?: string;
  phase?: string;
  fieldRestriction?: string;
}

const SECTORS = [
  'Cover', 'Point', 'Mid Off', 'Mid On',
  'Mid Wicket', 'Square Leg', 'Fine Leg', 'Third Man'
];

const BANDS = ['Inner', 'Mid', 'Deep'];

export const LiveDeliveryConsole: React.FC<LiveDeliveryConsoleProps> = ({
  batterName,
  bowlerName,
  matchFormat,
  over,
  ball,
  runs,
  wickets,
  tacticalObjective,
  venueId,
  environmentalConditions,
  onDeliveryLogged,
  onUndo,
  onReset,
  deliveryHistory = [],
  liveCommentary,
  phase = 'POWERPLAY',
  fieldRestriction = 'Max 2 Outside 30-Yard Circle (Powerplay)'
}) => {
  const [selectedOutcome, setSelectedOutcome] = useState<string>('0');
  const [selectedSector, setSelectedSector] = useState<string>('Cover');
  const [selectedBand, setSelectedBand] = useState<string>('Deep');
  const [wicketKind, setWicketKind] = useState<string>('caught_deep');
  const [isLogging, setIsLogging] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<'console' | 'history'>('console');

  const handleOutcomeClick = (val: string) => {
    setSelectedOutcome(val);
    if (val === '4' || val === '6') {
      setSelectedBand('Deep');
    } else if (val === '1' || val === '2' || val === '3') {
      setSelectedBand('Mid');
    } else if (val === '0') {
      setSelectedBand('Inner');
    }
  };

  const handleLogDelivery = async () => {
    setIsLogging(true);
    try {
      let runsBatter = 0;
      let extras = 0;
      let extraType = 'none';
      let isWicket = false;

      if (selectedOutcome === '0') runsBatter = 0;
      else if (selectedOutcome === '1') runsBatter = 1;
      else if (selectedOutcome === '2') runsBatter = 2;
      else if (selectedOutcome === '3') runsBatter = 3;
      else if (selectedOutcome === '4') runsBatter = 4;
      else if (selectedOutcome === '6') runsBatter = 6;
      else if (selectedOutcome === 'W') {
        isWicket = true;
        runsBatter = 0;
      } else if (selectedOutcome === 'Wd') {
        extras = 1;
        extraType = 'wide';
      } else if (selectedOutcome === 'Nb') {
        extras = 1;
        extraType = 'no_ball';
      }

      const payload = {
        batter_name: batterName,
        bowler_name: bowlerName,
        match_format: matchFormat,
        over,
        ball,
        runs_batter: runsBatter,
        extras,
        extra_type: extraType,
        shot_sector: selectedSector,
        shot_band: selectedBand,
        is_wicket: isWicket,
        wicket_kind: isWicket ? wicketKind : '',
        tactical_objective: tacticalObjective,
        ground_preset_id: venueId,
        environmental_conditions: environmentalConditions
      };

      const res = await fetch('/api/v1/match/delivery', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (res.ok) {
        const data = await res.json();
        onDeliveryLogged(data);
      }
    } catch (err) {
      console.error('Failed to log delivery', err);
    } finally {
      setIsLogging(false);
    }
  };

  const handleUndo = async () => {
    try {
      const res = await fetch('/api/v1/match/undo', { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        if (onUndo) onUndo(data);
      }
    } catch (err) {
      console.error('Failed to undo delivery', err);
    }
  };

  const handleReset = async () => {
    if (!window.confirm('Reset match score and clear delivery feed for this spell?')) return;
    try {
      const res = await fetch('/api/v1/match/reset', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          batter_name: batterName,
          bowler_name: bowlerName,
          match_format: matchFormat,
          starting_over: 0,
          starting_ball: 0,
          starting_runs: 0,
          starting_wickets: 0,
          tactical_objective: tacticalObjective,
          ground_preset_id: venueId
        })
      });
      if (res.ok) {
        const data = await res.json();
        if (onReset) onReset(data);
      }
    } catch (err) {
      console.error('Failed to reset match', err);
    }
  };

  const crr = over * 6 + ball > 0 ? ((runs / (over * 6 + ball)) * 6).toFixed(2) : '0.00';

  return (
    <div className="live-delivery-console-card cyber-glass">
      {/* Telemetry Header Strip */}
      <div className="console-telemetry-header">
        <div className="telemetry-live-status">
          <span className="pulse-led"></span>
          <span className="live-label font-mono">LIVE BALL-BY-BALL ENGINE</span>
        </div>

        <div className="telemetry-scoreboard">
          <div className="score-badge font-mono">
            <span className="sub-tag">SCORE</span>
            <span className="main-val">{runs}/{wickets}</span>
          </div>
          <div className="score-badge font-mono">
            <span className="sub-tag">OVERS</span>
            <span className="main-val">{over}.{ball}</span>
          </div>
          <div className="score-badge font-mono">
            <span className="sub-tag">CRR</span>
            <span className="main-val">{crr}</span>
          </div>
        </div>

        <div className="telemetry-restriction-pill font-mono">
          <span className="badge-icon">🛡️</span>
          <span>{phase} • {fieldRestriction}</span>
        </div>

        <div className="console-mode-toggle">
          <button
            type="button"
            className={`btn-mode-tab ${activeTab === 'console' ? 'active' : ''}`}
            onClick={() => setActiveTab('console')}
          >
            ⚡ Scorer
          </button>
          <button
            type="button"
            className={`btn-mode-tab ${activeTab === 'history' ? 'active' : ''}`}
            onClick={() => setActiveTab('history')}
          >
            📜 Feed ({deliveryHistory.length})
          </button>
        </div>
      </div>

      {activeTab === 'console' ? (
        <div className="console-body">
          {/* Top Outcome Bar */}
          <div className="console-row">
            <span className="row-title font-mono">DELIVERY OUTCOME</span>
            <div className="outcome-button-group">
              {[
                { id: '0', label: '•', desc: 'Dot' },
                { id: '1', label: '1', desc: 'Single' },
                { id: '2', label: '2', desc: 'Two' },
                { id: '3', label: '3', desc: 'Three' },
                { id: '4', label: '4', desc: 'FOUR', isFour: true },
                { id: '6', label: '6', desc: 'SIX', isSix: true },
                { id: 'W', label: 'W', desc: 'Wicket', isWicket: true },
                { id: 'Wd', label: 'Wd', desc: 'Wide' },
                { id: 'Nb', label: 'Nb', desc: 'No-Ball' },
              ].map((btn) => (
                <button
                  key={btn.id}
                  type="button"
                  className={`btn-outcome font-mono ${selectedOutcome === btn.id ? 'active' : ''} ${
                    btn.isFour ? 'four' : btn.isSix ? 'six' : btn.isWicket ? 'wicket' : ''
                  }`}
                  onClick={() => handleOutcomeClick(btn.id)}
                >
                  <span className="btn-label">{btn.label}</span>
                  <span className="btn-desc">{btn.desc}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Wicket options if Wicket is selected */}
          {selectedOutcome === 'W' && (
            <div className="wicket-options-row animate-fade-in">
              <span className="row-title font-mono text-crimson">DISMISSAL MODE</span>
              <div className="wicket-chips">
                {[
                  { id: 'caught_edge', label: 'Caught Edge / Behind' },
                  { id: 'caught_deep', label: 'Caught Deep Boundary' },
                  { id: 'bowled', label: 'Bowled / Castled' },
                  { id: 'lbw', label: 'LBW' },
                  { id: 'stumped', label: 'Stumped' },
                  { id: 'run_out', label: 'Run Out' },
                ].map((w) => (
                  <button
                    key={w.id}
                    type="button"
                    className={`btn-wicket-chip font-mono ${wicketKind === w.id ? 'active' : ''}`}
                    onClick={() => setWicketKind(w.id)}
                  >
                    {w.label}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Wagon Wheel Shot Direction Selector */}
          <div className="console-row">
            <div className="sector-selection-header">
              <span className="row-title font-mono">WAGON WHEEL SHOT SECTOR</span>
              <div className="band-toggle font-mono">
                {BANDS.map((b) => (
                  <button
                    key={b}
                    type="button"
                    className={`btn-band-pill ${selectedBand === b ? 'active' : ''}`}
                    onClick={() => setSelectedBand(b)}
                  >
                    {b} {b === 'Deep' ? '🧱' : b === 'Mid' ? '⭕' : '🎯'}
                  </button>
                ))}
              </div>
            </div>

            <div className="sector-grid">
              {SECTORS.map((sector) => (
                <button
                  key={sector}
                  type="button"
                  className={`btn-sector font-mono ${selectedSector === sector ? 'active' : ''}`}
                  onClick={() => setSelectedSector(sector)}
                >
                  <span className="sector-name">{sector}</span>
                  <span className="sector-zone-tag">{sector}_{selectedBand}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Execution Bar */}
          <div className="console-actions-bar">
            <div className="actions-left">
              <button
                type="button"
                className="btn-console-secondary font-mono"
                onClick={handleUndo}
                disabled={isLogging || deliveryHistory.length === 0}
                title="Revert previous delivery"
              >
                ↩ Undo Ball
              </button>
              <button
                type="button"
                className="btn-console-secondary font-mono text-muted"
                onClick={handleReset}
                disabled={isLogging}
                title="Reset innings state"
              >
                🔄 Reset
              </button>
            </div>

            <button
              type="button"
              className="btn-ingest-delivery font-mono"
              onClick={handleLogDelivery}
              disabled={isLogging}
            >
              {isLogging ? (
                <>⏳ OPTIMIZING 11 FIELDERS...</>
              ) : (
                <>
                  ⚡ LOG BALL {over}.{ball + 1 > 6 ? 1 : ball + 1} & ADAPT FIELD
                </>
              )}
            </button>
          </div>

          {/* Live Tactical Commentary Banner */}
          {liveCommentary && (
            <div className="live-commentary-banner animate-fade-in">
              <span className="commentary-icon">🎙️</span>
              <span className="commentary-text font-mono">{liveCommentary}</span>
            </div>
          )}
        </div>
      ) : (
        /* Delivery Feed History */
        <div className="console-history-pane animate-fade-in">
          {deliveryHistory.length === 0 ? (
            <div className="history-empty-state font-mono">
              No deliveries logged in this session yet. Use the Scorer tab to log deliveries and view real-time field morphing.
            </div>
          ) : (
            <div className="history-feed-list">
              {deliveryHistory.slice().reverse().map((item, idx) => (
                <div key={item.delivery_id || idx} className="history-delivery-card font-mono">
                  <div className="delivery-over-badge">
                    <span className="ball-num">{item.display_over}</span>
                    <span
                      className={`ball-outcome-badge ${
                        item.is_wicket
                          ? 'w'
                          : item.runs_batter === 4
                          ? 'four'
                          : item.runs_batter === 6
                          ? 'six'
                          : item.runs_batter === 0
                          ? 'dot'
                          : 'single'
                      }`}
                    >
                      {item.is_wicket ? 'W' : item.runs_batter}
                    </span>
                  </div>

                  <div className="delivery-detail">
                    <div className="delivery-meta">
                      <strong>{item.batter_name}</strong> facing <strong>{item.bowler_name}</strong> •{' '}
                      <span className="text-cyan">{item.shot_sector} ({item.shot_band})</span>
                      {item.wicket_kind && (
                        <span className="wicket-kind-pill">Dismissal: {item.wicket_kind}</span>
                      )}
                    </div>
                    <div className="delivery-adjustment-text">
                      ↳ {item.tactical_adjustment}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
