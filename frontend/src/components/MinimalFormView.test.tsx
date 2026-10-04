import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { MinimalFormView } from './MinimalFormView';

describe('MinimalFormView Component (Phase 5A)', () => {
  const mockPlayers = {
    batters: ['Virat Kohli', 'AB de Villiers', 'Chris Gayle'],
    bowlers: ['Mohammad Asif', 'Dale Steyn', 'Morne Morkel'],
    tactical_objectives: ['attack_wicket', 'prevent_boundary', 'build_pressure', 'stop_singles'],
    match_formats: ['T20', 'ODI'],
  };

  const mockAnalysisResponse = {
    analysis_id: 'test-uuid-1234',
    status: 'available',
    is_legal: true,
    violations: [],
    data_coverage: 'vs_bowler_type_phase',
    placements: [
      { position_name: '1st Slip', x: 3.5, y: -14.0, role: 'wicket_taking', reason: 'Catching edge', fielder: { name: 'Player 1' } },
      { position_name: '2nd Slip', x: 5.2, y: -13.2, role: 'wicket_taking', reason: 'Catching edge', fielder: { name: 'Player 2' } },
      { position_name: 'Gully', x: 7.5, y: -11.5, role: 'wicket_taking', reason: 'Catching edge', fielder: { name: 'Player 3' } },
      { position_name: 'Long On', x: 8.0, y: 55.0, role: 'run_saving', reason: 'Boundary prevention', fielder: { name: 'Player 4' } },
      { position_name: 'Deep Extra Cover', x: 45.0, y: 35.0, role: 'run_saving', reason: 'Boundary prevention', fielder: { name: 'Player 5' } },
      { position_name: 'Extra Cover', x: 22.0, y: 15.0, role: 'run_saving', reason: 'Ring saving', fielder: { name: 'Player 6' } },
      { position_name: 'Point', x: 25.0, y: -5.0, role: 'run_saving', reason: 'Ring saving', fielder: { name: 'Player 7' } },
      { position_name: 'Backward Point', x: 20.0, y: -12.0, role: 'run_saving', reason: 'Ring saving', fielder: { name: 'Player 8' } },
      { position_name: 'Square Leg', x: -22.0, y: -5.0, role: 'run_saving', reason: 'Ring saving', fielder: { name: 'Player 9' } },
      { position_name: 'Wicketkeeper', x: 0.0, y: -15.0, role: 'core', reason: 'Core keeper position', fielder: { name: 'Player 10' } },
      { position_name: 'Bowler', x: 0.0, y: 10.0, role: 'core', reason: 'Core bowler position', fielder: { name: 'Player 11' } },
    ],
    matchup_stats: {
      has_history: true,
      balls_faced: 232,
      runs_scored: 288,
      dismissals: 4,
      strike_rate: 124.14,
      dot_ball_pct: 40.09,
      boundary_pct: 18.97,
      source: 'vs_bowler_type_phase',
      data_coverage_note: 'Fallback tier 2: 232 balls faced vs Pace in POWERPLAY phase',
    },
    model_confidence: {
      wicket_prediction_recall: 0.02,
      wicket_prediction_precision: 0.167,
      status: 'uncalibrated_baseline',
    },
    ml_probabilities: {
      dot_pct: 0.40,
      single_pct: 0.35,
      two_pct: 0.06,
      boundary_pct: 0.15,
      four_pct: 0.11,
      six_pct: 0.04,
      wicket_pct: 0.04,
      expected_runs_per_ball: 1.12,
    },
    bowler_provenance: {
      bowler_type: 'curated_categorical',
      new_ball_strength: 'synthetic_estimate',
      death_bowling_strength: 'synthetic_estimate',
    },
  };

  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn((url: string) => {
      if (url.includes('/api/v1/players')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockPlayers),
        });
      }
      if (url.includes('/api/v1/analysis')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockAnalysisResponse),
        });
      }
      return Promise.reject(new Error(`Unhandled URL: ${url}`));
    }));
  });

  it('renders inputs and populates dynamic options from /api/v1/players', async () => {
    render(<MinimalFormView />);

    // Check header
    expect(screen.getByText(/Phase 5A Minimal Client/i)).toBeInTheDocument();

    // Wait for player options to load
    await waitFor(() => {
      expect(screen.getByLabelText(/Batter/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/Bowler/i)).toBeInTheDocument();
    });

    expect(screen.getByDisplayValue('Virat Kohli')).toBeInTheDocument();
    expect(screen.getByDisplayValue('Mohammad Asif')).toBeInTheDocument();
  });

  it('submits form and renders 11 placements, legality status, and explicit confidence', async () => {
    render(<MinimalFormView />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Generate Field/i })).toBeInTheDocument();
    });

    // Click submit
    fireEvent.click(screen.getByRole('button', { name: /Generate Field/i }));

    // Assert results appear
    await waitFor(() => {
      expect(screen.getByText(/LEGAL \(All ICC Constraints Satisfied\)/i)).toBeInTheDocument();
    });

    // Check Placements Table
    const table = screen.getByRole('table');
    expect(table).toBeInTheDocument();
    expect(screen.getByText('1st Slip')).toBeInTheDocument();
    expect(screen.getByText('Wicketkeeper')).toBeInTheDocument();
    expect(screen.getByText('Bowler')).toBeInTheDocument();

    // Check Data Coverage & Provenance Card
    expect(screen.getByText(/Fallback tier 2: 232 balls faced vs Pace in POWERPLAY phase/i)).toBeInTheDocument();
    expect(screen.getByText(/124.14/)).toBeInTheDocument();
    expect(screen.getByText(/40.09%/)).toBeInTheDocument();

    // Check Model Confidence Card
    expect(screen.getByText(/Measured Wicket Recall:/i)).toBeInTheDocument();
    expect(screen.getByText(/2.0%/i)).toBeInTheDocument();
    expect(screen.getByText(/16.7%/i)).toBeInTheDocument();
    expect(screen.getByText('uncalibrated_baseline')).toBeInTheDocument();
  });
});
