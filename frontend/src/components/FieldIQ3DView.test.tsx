import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { FieldIQ3DView } from './FieldIQ3DView';

const mockPlayersData = {
  batters: [
    'Virat Kohli',
    'Rohit Sharma',
    'Babar Azam',
    'Kane Williamson',
    'Joe Root',
    'Steve Smith',
    'David Warner',
    'KL Rahul',
    'Rishabh Pant',
  ],
  bowlers: [
    'Jasprit Bumrah',
    'Mohammad Asif',
    'Shaheen Afridi',
    'Pat Cummins',
    'Mitchell Starc',
    'Trent Boult',
    'Rashid Khan',
    'Generic Right-Arm Fast',
  ],
  tactical_objectives: [
    'attack_wicket',
    'prevent_boundary',
    'build_pressure',
    'stop_singles',
  ],
  match_formats: ['T20', 'ODI'],
};

const mockAnalysisResponse = {
  analysis_id: 'test-3d-analysis-001',
  status: 'optimized',
  data_driven: true,
  reason: 'Simulated 3D tactical evaluation',
  placements: [
    { position_name: 'Wicket Keeper', x: 0.0, y: -16.0, role: 'core', reason: 'Behind stumps regulation keeper' },
    { position_name: 'Bowler', x: 0.0, y: 10.0, role: 'core', reason: 'Active delivery follow-through' },
    { position_name: '1st Slip', x: 3.5, y: -14.0, role: 'wicket_taking', reason: 'Catching edge off seam' },
    { position_name: '2nd Slip', x: 5.5, y: -13.0, role: 'wicket_taking', reason: 'Thick outside edge catching' },
    { position_name: 'Gully', x: 12.0, y: -9.0, role: 'wicket_taking', reason: 'Square flying edge patrol' },
    { position_name: 'Point', x: 22.0, y: -2.0, role: 'run_saving', reason: 'Square cut interception ring' },
    { position_name: 'Cover', x: 20.0, y: 10.0, role: 'run_saving', reason: 'Off-drive ring pressure' },
    { position_name: 'Mid Off', x: 14.0, y: 22.0, role: 'run_saving', reason: 'Straight drive deterrence' },
    { position_name: 'Mid On', x: -14.0, y: 22.0, role: 'run_saving', reason: 'On-drive deterrence' },
    { position_name: 'Mid Wicket', x: -20.0, y: 10.0, role: 'run_saving', reason: 'Pull and flick ring containment' },
    { position_name: 'Fine Leg', x: -24.0, y: -38.0, role: 'boundary_rider', reason: 'Hook and pull boundary security' },
  ],
  ers: 3.42,
  ewo: 0.18,
  cds: 82.5,
  tactical_explanations: ['Attacking field deployed for Virat Kohli vs Mohammad Asif'],
  is_legal: true,
  violations: [],
  matchup_stats: {
    has_history: true,
    balls_faced: 232,
    runs_scored: 184,
    dismissals: 4,
    strike_rate: 79.3,
    dot_ball_pct: 48.2,
    source: 'vs_bowler_type_phase',
    data_coverage_note: 'Aggregated against right-arm fast in Powerplay',
  },
  data_coverage: 'vs_bowler_type_phase',
  model_confidence: {
    status: 'uncalibrated_baseline',
    wicket_recall: 0.02,
    wicket_precision: 0.167,
    message: 'Baseline probabilistic model trained on T20/ODI historical deliveries',
  },
  bowler_provenance: {
    source: 'real_data',
    name: 'Mohammad Asif',
  },
  zone_chart: {
    zone_1: 0.12,
    zone_2: 0.08,
  },
};

describe('FieldIQ3DView Component', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    globalThis.fetch = vi.fn().mockImplementation((url: string) => {
      if (url === '/api/v1/players') {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockPlayersData),
        });
      }
      if (url === '/api/v1/analysis') {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockAnalysisResponse),
        });
      }
      return Promise.reject(new Error(`Unhandled request: ${url}`));
    });
  });

  it('renders initial form with real player options from GET /api/v1/players', async () => {
    render(<FieldIQ3DView />);

    expect(screen.getByText('FieldIQ — 3D Cricket Tactical Intelligence')).toBeInTheDocument();

    // Verify batter select loads dynamic options
    await waitFor(() => {
      const batterSelect = screen.getByLabelText(/batter/i) as HTMLSelectElement;
      expect(batterSelect.value).toBe('Virat Kohli');
    });

    const batterSelect = screen.getByLabelText(/batter/i);
    expect(batterSelect).toBeInTheDocument();
    expect(screen.getByRole('option', { name: 'Rohit Sharma' })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: 'Babar Azam' })).toBeInTheDocument();

    // Verify datalist contains bowlers
    const datalist = document.getElementById('bowler-options');
    expect(datalist).toBeInTheDocument();
    expect(datalist?.children.length).toBe(8);

    // Verify 1-indexed over select contains phase descriptions
    expect(screen.getByRole('option', { name: 'Over 3 — Powerplay' })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: 'Over 10 — Middle' })).toBeInTheDocument();
  });

  it('submits form, renders canvas, server legality banner, data coverage tier, and confidence disclosures', async () => {
    const user = userEvent.setup();
    const { container } = render(<FieldIQ3DView />);

    // Wait for player options to load
    await screen.findByRole('option', { name: 'Virat Kohli' });

    // Submit the tactical analysis form
    const submitBtn = screen.getByRole('button', { name: /generate 3d tactical field/i });
    await user.click(submitBtn);

    // Verify server legality banner (display-only)
    await screen.findByText('✓ LEGAL FIELD CONFIGURATION');
    expect(screen.getByText('Complies with all ICC fielding regulations')).toBeInTheDocument();

    // Verify WebGL Canvas is actually rendered in DOM
    const canvasElement = container.querySelector('canvas');
    expect(canvasElement).toBeInTheDocument();

    // Verify Matchup Intelligence Tier card rendered with provenance/tier
    const coverageCard = document.getElementById('data-coverage-card');
    expect(coverageCard).toBeInTheDocument();
    expect(screen.getByText('vs_bowler_type_phase')).toBeInTheDocument();
    expect(screen.getByText('232')).toBeInTheDocument(); // Balls faced
    expect(screen.getByText('Aggregated against right-arm fast in Powerplay')).toBeInTheDocument();

    // Verify Model Confidence Disclosure card rendered without masking limitations
    const confidenceCard = document.getElementById('model-confidence-card');
    expect(confidenceCard).toBeInTheDocument();
    expect(screen.getByText('uncalibrated_baseline')).toBeInTheDocument();
    expect(screen.getByText('2.0%')).toBeInTheDocument(); // 0.02 * 100
    expect(screen.getByText('16.7%')).toBeInTheDocument(); // 0.167 * 100

    // Verify 11 fielders table
    expect(screen.getByText('11 Recommended Field Placements')).toBeInTheDocument();
    expect(screen.getByText('Wicket Keeper')).toBeInTheDocument();
    expect(screen.getByText('1st Slip')).toBeInTheDocument();
    expect(screen.getByText('2nd Slip')).toBeInTheDocument();
    expect(screen.getByText('Gully')).toBeInTheDocument();
    expect(screen.getByText('Point')).toBeInTheDocument();
    expect(screen.getByText('Fine Leg')).toBeInTheDocument();

    // Verify fetch call payload
    expect(globalThis.fetch).toHaveBeenCalledWith(
      '/api/v1/analysis',
      expect.objectContaining({
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      })
    );
  });
});
