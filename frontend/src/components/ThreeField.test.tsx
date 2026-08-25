import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MatchContextPanel } from './MatchContextPanel';
import { TacticalPanel, FielderPosition } from './TacticalPanel';

describe('MatchContextPanel Component', () => {
  it('renders form inputs and handles form submission', async () => {
    const user = userEvent.setup();
    const mockSubmit = vi.fn();
    render(<MatchContextPanel onSubmit={mockSubmit} loading={false} />);

    // Check header
    expect(screen.getByText('Match Situation Setup')).toBeInTheDocument();

    // Fill in Batter name
    const batterInput = screen.getByLabelText(/batter name/i);
    await user.clear(batterInput);
    await user.type(batterInput, 'Sachin Tendulkar');

    // Fill in Bowler name
    const bowlerInput = screen.getByLabelText(/bowler name/i);
    await user.clear(bowlerInput);
    await user.type(bowlerInput, 'Shane Warne');

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
      batter_name: 'Sachin Tendulkar',
      bowler_name: 'Shane Warne',
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
