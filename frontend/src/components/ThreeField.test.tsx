import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MatchContextPanel } from './MatchContextPanel';
import { TacticalPanel, FielderPosition } from './TacticalPanel';

describe('MatchContextPanel Component', () => {
  beforeEach(() => {
    global.fetch = vi.fn().mockImplementation(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({
          batters: ['Virat Kohli', 'AB de Villiers', 'Brendon McCullum', 'David Warner'],
          bowlers: ['Mitchell Starc', 'Jasprit Bumrah', 'Left-Arm Fast', 'Leg-Spinner']
        })
      })
    );
  });

  it('renders form inputs and handles form submission', async () => {
    const user = userEvent.setup();
    const mockSubmit = vi.fn();
    render(<MatchContextPanel onSubmit={mockSubmit} loading={false} />);

    // Check header
    expect(screen.getByText('TACTICAL CONTROL')).toBeInTheDocument();

    // Wait for players list to fetch and load
    await screen.findByRole('option', { name: 'AB de Villiers' });

    // Select Batter name
    const batterSelect = screen.getByLabelText(/active batter/i);
    fireEvent.change(batterSelect, { target: { value: 'AB de Villiers' } });

    // Select Bowler name
    const bowlerSelect = screen.getByLabelText(/active bowler/i);
    fireEvent.change(bowlerSelect, { target: { value: 'Jasprit Bumrah' } });

    // Change tactical objective by clicking the Prevent Boundary card
    const preventBoundaryCard = screen.getByRole('button', { name: /prevent boundary/i });
    await user.click(preventBoundaryCard);

    // Submit form
    const submitBtn = screen.getByRole('button', { name: /recommend tactical field/i });
    await user.click(submitBtn);

    expect(mockSubmit).toHaveBeenCalledWith({
      match_format: 'ODI',
      innings: 1,
      over: 4,
      runs: 18,
      wickets: 0,
      batter_name: 'AB de Villiers',
      bowler_name: 'Jasprit Bumrah',
      tactical_objective: 'prevent_boundary',
    });
  });
});

describe('TacticalPanel Component', () => {
  const sampleFielders: FielderPosition[] = [
    { name: '1st Slip', x: 3.5, y: -14.0, role: 'wicket_taking' },
    { name: 'Point', x: 22.0, y: -2.0, role: 'run_saving' },
  ];

  it('renders coordinate table and displays metrics', async () => {
    const mockReset = vi.fn();
    render(
      <TacticalPanel
        fielders={sampleFielders}
        onReset={mockReset}
        objective="attack_wicket"
      />
    );

    // Verify metrics are displayed
    expect(screen.getByText('Expected Wicket')).toBeInTheDocument();
    expect(screen.getByText('Runs Saved (ERS)')).toBeInTheDocument();
    expect(screen.getByText('Defensive Score (CDS)')).toBeInTheDocument();

    // Verify coordinate table shows the fielders
    expect(screen.getByText('1st Slip')).toBeInTheDocument();
    expect(screen.getByText('3.5')).toBeInTheDocument();
    expect(screen.getByText('-14.0')).toBeInTheDocument();
    expect(screen.getByText('Point')).toBeInTheDocument();

    // Verify report exporter button exists
    expect(screen.getByRole('button', { name: /export report/i })).toBeInTheDocument();
  });
});
