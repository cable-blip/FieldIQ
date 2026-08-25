import React, { useState } from 'react';
import './MappingForm.css';

// Canonical fields lists from the contract
export const REQUIRED_FIELDS = [
  'match_id',
  'innings',
  'delivery_number',
  'batter_name',
  'bowler_name',
  'runs_batter',
  'runs_extras',
  'runs_total',
  'is_wicket',
];

export const OPTIONAL_FIELDS = [
  'match_format',
  'batting_team',
  'bowling_team',
  'venue',
  'match_date',
  'non_striker_name',
  'wicket_type',
  'dismissed_batter',
  'delivery_line',
  'delivery_length',
  'release_speed_kph',
  'pitch_coordinates_x',
  'pitch_coordinates_y',
  'shot_coordinates_x',
  'shot_coordinates_y',
  'field_placement_id',
  'fielder_outcome',
];

interface MappingIssue {
  canonical_field?: string | null;
  source_field?: string | null;
  code: string;
  message: string;
}

interface MappingReport {
  mapping_status: 'valid' | 'invalid';
  mapped_columns: Record<string, string>;
  unmapped_source_columns: string[];
  issues: MappingIssue[];
}

export const MappingForm: React.FC = () => {
  const [rawHeaders, setRawHeaders] = useState<string>('game_id, innings_no, ball_seq, striker, bowler, runs_off_bat, extra_runs, total_runs, wicket, ground_name');
  const [sourceHeaders, setSourceHeaders] = useState<string[]>([]);
  const [columnMapping, setColumnMapping] = useState<Record<string, string>>({});
  const [validationReport, setValidationReport] = useState<MappingReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);

  const handleParseHeaders = () => {
    const headers = rawHeaders
      .split(',')
      .map((h) => h.trim())
      .filter((h) => h.length > 0);
    setSourceHeaders(headers);
    // Reset mapping and validation status when headers change
    setColumnMapping({});
    setValidationReport(null);
    setError(null);
  };

  const handleSelectMapping = (canonicalField: string, sourceHeader: string) => {
    setColumnMapping((prev) => {
      const next = { ...prev };
      if (!sourceHeader) {
        delete next[canonicalField];
      } else {
        next[canonicalField] = sourceHeader;
      }
      return next;
    });
  };

  const handleValidateMapping = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setValidationReport(null);

    try {
      const response = await fetch('/api/v1/datasets/column-mappings/validate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          source_headers: sourceHeaders,
          column_mapping: columnMapping,
        }),
      });

      if (!response.ok) {
        throw new Error(`Server returned HTTP ${response.status}`);
      }

      const report: MappingReport = await response.json();
      setValidationReport(report);
    } catch (err: any) {
      setError(err.message || 'Failed to validate mapping.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mapping-container">
      <h2>FieldIQ Dataset Column Mapping</h2>
      <p className="description">
        Configure the mapping from your source CSV headers to the FieldIQ canonical contract.
      </p>

      {/* Header Parsing Section */}
      <div className="card">
        <h3>1. Source Headers</h3>
        <p className="instruction">
          Enter your CSV headers as a comma-separated list:
        </p>
        <textarea
          rows={3}
          value={rawHeaders}
          onChange={(e) => setRawHeaders(e.target.value)}
          placeholder="e.g. match, innings, delivery, batsman, bowler..."
          className="headers-textarea"
        />
        <button type="button" onClick={handleParseHeaders} className="btn btn-primary">
          Parse & Load Headers
        </button>
        {sourceHeaders.length > 0 && (
          <div className="parsed-headers">
            <strong>Loaded Headers ({sourceHeaders.length}):</strong>
            <div className="badge-container">
              {sourceHeaders.map((header) => (
                <span key={header} className="badge">
                  {header}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {sourceHeaders.length > 0 && (
        <form onSubmit={handleValidateMapping}>
          {/* Mapping Grid */}
          <div className="card">
            <h3>2. Map Canonical Fields</h3>
            
            <div className="mapping-section">
              <h4>Required Fields *</h4>
              <p className="instruction">All required fields must be mapped to valid source headers.</p>
              <div className="fields-grid">
                {REQUIRED_FIELDS.map((field) => (
                  <div key={field} className="field-row">
                    <label htmlFor={`req-${field}`} className="field-label required">
                      {field} <span className="indicator">*</span>
                    </label>
                    <select
                      id={`req-${field}`}
                      value={columnMapping[field] || ''}
                      onChange={(e) => handleSelectMapping(field, e.target.value)}
                      className="field-select"
                    >
                      <option value="">-- Select source header --</option>
                      {sourceHeaders.map((header) => (
                        <option key={header} value={header}>
                          {header}
                        </option>
                      ))}
                    </select>
                  </div>
                ))}
              </div>
            </div>

            <div className="mapping-section">
              <h4>Optional Fields</h4>
              <p className="instruction">Optional fields will be marked as unavailable if not mapped.</p>
              <div className="fields-grid">
                {OPTIONAL_FIELDS.map((field) => (
                  <div key={field} className="field-row">
                    <label htmlFor={`opt-${field}`} className="field-label">
                      {field}
                    </label>
                    <select
                      id={`opt-${field}`}
                      value={columnMapping[field] || ''}
                      onChange={(e) => handleSelectMapping(field, e.target.value)}
                      className="field-select"
                    >
                      <option value="">-- Unavailable (not mapped) --</option>
                      {sourceHeaders.map((header) => (
                        <option key={header} value={header}>
                          {header}
                        </option>
                      ))}
                    </select>
                  </div>
                ))}
              </div>
            </div>

            <div className="form-actions">
              <button
                type="submit"
                disabled={loading}
                className="btn btn-success btn-large"
              >
                {loading ? 'Validating...' : '🎯 Validate Mapping Configuration'}
              </button>
            </div>
          </div>
        </form>
      )}

      {/* Error Message */}
      {error && (
        <div className="alert alert-danger">
          <strong>Error:</strong> {error}
        </div>
      )}

      {/* Validation Results Report */}
      {validationReport && (
        <div className={`card report-card ${validationReport.mapping_status}`}>
          <h3>3. Mapping Validation Result</h3>
          
          <div className="report-header">
            Status:{' '}
            <span className={`status-badge ${validationReport.mapping_status}`}>
              {validationReport.mapping_status.toUpperCase()}
            </span>
          </div>

          {/* Validation Issues */}
          {validationReport.issues.length > 0 && (
            <div className="report-section">
              <h4>Validation Issues ({validationReport.issues.length})</h4>
              <ul className="issues-list">
                {validationReport.issues.map((issue, idx) => (
                  <li key={idx} className="issue-item">
                    <span className="issue-code">[{issue.code}]</span>{' '}
                    {issue.canonical_field && (
                      <span className="issue-target">Canonical: {issue.canonical_field}</span>
                    )}{' '}
                    {issue.source_field && (
                      <span className="issue-source">Source: {issue.source_field}</span>
                    )}{' '}
                    <p className="issue-message">{issue.message}</p>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Mapped Columns summary */}
          <div className="report-section">
            <h4>Mapped Fields</h4>
            {Object.keys(validationReport.mapped_columns).length === 0 ? (
              <p className="empty-text">No columns mapped.</p>
            ) : (
              <div className="table-responsive">
                <table className="report-table">
                  <thead>
                    <tr>
                      <th>Canonical Name</th>
                      <th>Source Header</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(validationReport.mapped_columns).map(([canonical, source]) => (
                      <tr key={canonical}>
                        <td className="font-mono">{canonical}</td>
                        <td className="font-mono">{source}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Unmapped Source Columns */}
          <div className="report-section">
            <h4>Unmapped Source Columns ({validationReport.unmapped_source_columns.length})</h4>
            {validationReport.unmapped_source_columns.length === 0 ? (
              <p className="empty-text">All source columns successfully mapped!</p>
            ) : (
              <div className="badge-container">
                {validationReport.unmapped_source_columns.map((col) => (
                  <span key={col} className="badge badge-unmapped">
                    {col}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
