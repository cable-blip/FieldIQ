import { render, screen, fireEvent, waitFor } from '@testing-library/react';
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
    expect(screen.getByText('Match Situation Setup')).toBeInTheDocument();

    // Wait for players list to fetch and load
    await screen.findByRole('option', { name: 'AB de Villiers' });

    // Select Batter name
    const batterSelect = screen.getByLabelText(/batter name/i);
    fireEvent.change(batterSelect, { target: { value: 'AB de Villiers' } });

    // Select Bowler name
    const bowlerSelect = screen.getByLabelText(/bowler name/i);
    fireEvent.change(bowlerSelect, { target: { value: 'Jasprit Bumrah' } });

    // Change tactical objective
    const objectiveSelect = screen.getByLabelText(/tactical objective/i);
    fireEvent.change(objectiveSelect, { target: { value: 'prevent_boundary' } });

    // Submit form
    const submitBtn = screen.getByRole('button', { name: /recommend tactical field/i });
    await user.click(submitBtn);

    expect(mockSubmit).toHaveBeenCalledWith({
      match_format: 'ODI',
      innings: 1,
      over: 1,
      runs: 0,
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

  it('renders coordinate table and triggers reset', async () => {
    const user = userEvent.setup();
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

    // Click reset
    const resetBtn = screen.getByRole('button', { name: /reset positions/i });
    await user.click(resetBtn);

    expect(mockReset).toHaveBeenCalled();
  });
});
