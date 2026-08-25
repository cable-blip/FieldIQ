import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { MappingForm, REQUIRED_FIELDS } from './MappingForm';

describe('MappingForm Component', () => {
  const mockFetch = vi.fn();

  beforeEach(() => {
    vi.stubGlobal('fetch', mockFetch);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders header parsing textarea and loads headers on click', async () => {
    const user = userEvent.setup();
    render(<MappingForm />);
    
    // Check main title
    expect(screen.getByText('FieldIQ Dataset Column Mapping')).toBeInTheDocument();
    
    const textarea = screen.getByPlaceholderText(/e.g. match, innings/i);
    expect(textarea).toBeInTheDocument();
    
    // Clear and type new values using user-event
    await user.clear(textarea);
    await user.type(textarea, 'col_a, col_b, col_c');
    
    const parseBtn = screen.getByRole('button', { name: /parse & load headers/i });
    await user.click(parseBtn);
    
    // Check that badges are rendered specifically (targeting elements with class .badge to ignore dropdown options)
    expect(screen.getByText('col_a', { selector: '.badge' })).toBeInTheDocument();
    expect(screen.getByText('col_b', { selector: '.badge' })).toBeInTheDocument();
    expect(screen.getByText('col_c', { selector: '.badge' })).toBeInTheDocument();
  });

  it('renders dropdowns for required and optional fields', async () => {
    const user = userEvent.setup();
    render(<MappingForm />);
    
    // Load some headers first
    const parseBtn = screen.getByRole('button', { name: /parse & load headers/i });
    await user.click(parseBtn);
    
    // Verify required section exists
    expect(screen.getByText('Required Fields *')).toBeInTheDocument();
    
    // Verify optional section exists
    expect(screen.getByText('Optional Fields')).toBeInTheDocument();

    // Verify some select boxes exist
    REQUIRED_FIELDS.forEach((field) => {
      const select = screen.getByLabelText(new RegExp(`^${field}\\s*\\*?$`, 'i'));
      expect(select).toBeInTheDocument();
    });
  });

  it('handles successful API validation response', async () => {
    const user = userEvent.setup();
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        mapping_status: 'valid',
        mapped_columns: {
          match_id: 'game_id',
          innings: 'innings_no',
        },
        unmapped_source_columns: ['extra_col'],
        issues: [],
      }),
    });

    render(<MappingForm />);
    
    // Load headers
    const parseBtn = screen.getByRole('button', { name: /parse & load headers/i });
    await user.click(parseBtn);
    
    // Set a dropdown value
    const matchIdSelect = screen.getByLabelText(/^match_id\s*\*?$/i);
    fireEvent.change(matchIdSelect, { target: { value: 'game_id' } });
    
    const validateBtn = screen.getByRole('button', { name: /validate mapping configuration/i });
    await user.click(validateBtn);
    
    await waitFor(() => {
      expect(screen.getByText('VALID')).toBeInTheDocument();
    });

    // Verify that columns are in the mapped table
    const matchIdElements = screen.getAllByText('match_id');
    expect(matchIdElements.length).toBeGreaterThan(0);
    
    const gameIdElements = screen.getAllByText('game_id');
    expect(gameIdElements.length).toBeGreaterThan(0);
    
    expect(screen.getByText('extra_col', { selector: '.badge' })).toBeInTheDocument();
  });

  it('handles invalid API validation response with issues', async () => {
    const user = userEvent.setup();
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        mapping_status: 'invalid',
        mapped_columns: {},
        unmapped_source_columns: [],
        issues: [
          {
            canonical_field: 'runs_total',
            code: 'missing_required_mapping',
            message: 'A source column must be mapped for this required field.',
          },
        ],
      }),
    });

    render(<MappingForm />);
    
    // Load headers
    const parseBtn = screen.getByRole('button', { name: /parse & load headers/i });
    await user.click(parseBtn);
    
    const validateBtn = screen.getByRole('button', { name: /validate mapping configuration/i });
    await user.click(validateBtn);
    
    await waitFor(() => {
      expect(screen.getByText('INVALID')).toBeInTheDocument();
    });

    expect(screen.getByText('[missing_required_mapping]')).toBeInTheDocument();
    expect(screen.getByText('A source column must be mapped for this required field.')).toBeInTheDocument();
  });
});
