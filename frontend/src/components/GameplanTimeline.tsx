import React from 'react';
import './GameplanTimeline.css';

export interface GameplanOverItem {
  over_number: number;
  phase: string;
  tactical_objective: string;
  bowler_recommended_channel: string;
  bowler_recommended_length: string;
  suggested_variations: string[];
  tactical_directive: string;
  ers: number;
  ewo: number;
  cds: number;
  is_legal: boolean;
  placements: any[];
  outcome_probabilities?: {
    dot_pct: number;
    boundary_pct: number;
    wicket_pct: number;
    expected_runs_per_ball: number;
  };
}

interface GameplanTimelineProps {
  sequence: GameplanOverItem[];
  activeOverIndex: number;
  onSelectOver: (index: number) => void;
  groundName?: string;
  pitchType?: string;
}

export const GameplanTimeline: React.FC<GameplanTimelineProps> = ({
  sequence,
  activeOverIndex,
  onSelectOver,
  groundName = "Lord's",
  pitchType = 'green_seam'
}) => {
  if (!sequence || sequence.length === 0) return null;

  return (
    <div className="gameplan-timeline-container">
      <div className="timeline-header">
        <div className="timeline-title-wrap">
          <span className="timeline-badge font-mono">STRATEGIC GAMEPLAN SEQUENCE</span>
          <span className="timeline-meta font-mono">
            {sequence.length} OVERS · {groundName.toUpperCase()} · {pitchType.replace('_', ' ').toUpperCase()}
          </span>
        </div>
        <span className="timeline-hint font-mono">Click over card to morph 3D field</span>
      </div>

      <div className="timeline-scroll-strip">
        {sequence.map((item, idx) => {
          const isActive = idx === activeOverIndex;
          const probs = item.outcome_probabilities;

          return (
            <div
              key={item.over_number}
              className={`timeline-card ${isActive ? 'active' : ''}`}
              onClick={() => onSelectOver(idx)}
            >
              {/* Over Number & Phase Badge */}
              <div className="card-top-row">
                <span className="over-pill font-mono">OVER {item.over_number}</span>
                <span className={`phase-tag ${item.phase.toLowerCase()} font-mono`}>
                  {item.phase}
                </span>
              </div>

              {/* Bowling Channel & Length */}
              <div className="bowling-directive-box">
                <div className="channel-line">
                  <span className="dir-icon">🎯</span>
                  <span className="channel-name">{item.bowler_recommended_channel}</span>
                </div>
                <div className="length-line font-mono">
                  📏 {item.bowler_recommended_length}
                </div>
              </div>

              {/* Delivery Variations */}
              {item.suggested_variations && item.suggested_variations.length > 0 && (
                <div className="variations-cluster">
                  {item.suggested_variations.slice(0, 2).map((v, vIdx) => (
                    <span key={vIdx} className="variation-chip font-mono">
                      {v}
                    </span>
                  ))}
                </div>
              )}

              {/* Tactical Directive Excerpt */}
              <p className="directive-quote font-mono">
                "{item.tactical_directive}"
              </p>

              {/* Quick Telemetry Footnote */}
              {probs && (
                <div className="card-telemetry-row font-mono">
                  <span className="prob-stat dots">⚪ {probs.dot_pct.toFixed(0)}% Dot</span>
                  <span className="prob-stat wickets">🟣 {probs.wicket_pct.toFixed(1)}% Wkt</span>
                  <span className="prob-stat boundary">🔴 {probs.boundary_pct.toFixed(0)}% Bnd</span>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
