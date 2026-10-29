import React, { useState, useEffect, useRef } from 'react';
import './DatasetStudioModal.css';

interface DatasetProvenance {
  dataset_name: string;
  dataset_version: string;
  derived_dataset_version?: string;
  primary_source_repository?: string;
  primary_source_url?: string;
  primary_source_license?: string;
  spatial_source_description?: string;
  ball_by_ball_enrichment_source?: string;
  ball_by_ball_enrichment_license?: string;
  enrichment_method?: string;
  row_count?: number;
  batter_count?: number;
  bowler_count?: number;
  match_count?: number;
  valid_directional_count?: number;
  zone_0_count?: number;
  validation_status?: string;
  known_limitations?: string[];
  governance_classification?: string;
}

interface DatasetSummary {
  status: string;
  total_deliveries: number;
  total_matches: number;
  unique_batters_count: number;
  unique_bowlers_count: number;
  batters: string[];
  bowlers: string[];
  missing_zone_deliveries?: number;
  missing_zone_pct?: number;
  last_updated: string;
  provenance?: DatasetProvenance;
}

interface DatasetStudioModalProps {
  isOpen: boolean;
  onClose: () => void;
  onDatasetUpdated?: () => void;
}

export const DatasetStudioModal: React.FC<DatasetStudioModalProps> = ({
  isOpen,
  onClose,
  onDatasetUpdated
}) => {
  const [summary, setSummary] = useState<DatasetSummary | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [uploading, setUploading] = useState<boolean>(false);
  const [uploadProgress, setUploadProgress] = useState<string>('');
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [isDragOver, setIsDragOver] = useState<boolean>(false);
  
  const fileInputRef = useRef<HTMLInputElement>(null);
  const folderInputRef = useRef<HTMLInputElement>(null);

  const fetchSummary = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/v1/dataset/summary');
      if (res.ok) {
        const data = await res.json();
        setSummary(data);
      }
    } catch {
      // Ignore network errors in local dev
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchSummary();
      setMessage(null);
      setUploadProgress('');
    }
  }, [isOpen]);

  const handleFilesUpload = async (fileList: FileList | File[]) => {
    const filesArray = Array.from(fileList);
    if (filesArray.length === 0) return;

    setUploading(true);
    setMessage(null);
    setUploadProgress(`Processing and uploading ${filesArray.length} match dataset files...`);

    const formData = new FormData();
    filesArray.forEach((f) => {
      formData.append('files', f);
    });

    try {
      const res = await fetch('/api/v1/dataset/upload', {
        method: 'POST',
        body: formData,
      });

      const data = await res.json();
      if (res.ok) {
        setMessage({
          type: 'success',
          text: data.message || `Successfully ingested ${filesArray.length} dataset files!`,
        });
        if (data.summary) {
          setSummary(data.summary);
        }
        if (onDatasetUpdated) onDatasetUpdated();
      } else {
        setMessage({ type: 'error', text: data.detail || 'Batch upload failed. Please verify format.' });
      }
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || 'Network error during dataset upload.' });
    } finally {
      setUploading(false);
      setUploadProgress('');
    }
  };

  const handleRetrain = async () => {
    setLoading(true);
    setMessage(null);
    try {
      const res = await fetch('/api/v1/dataset/retrain', {
        method: 'POST',
      });
      const data = await res.json();
      if (res.ok) {
        setMessage({ type: 'success', text: '✅ Bayesian ML model likelihoods and player profiles refreshed!' });
        if (data.summary) setSummary(data.summary);
        if (onDatasetUpdated) onDatasetUpdated();
      } else {
        setMessage({ type: 'error', text: data.detail || 'Retraining failed.' });
      }
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || 'Error during model retraining.' });
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  const prov = summary?.provenance;

  return (
    <div className="dataset-modal-backdrop" onClick={onClose}>
      <div className="dataset-modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="dataset-modal-header">
          <div className="header-brand">
            <span className="hub-icon">📂</span>
            <div>
              <h3>Real-Life Dataset Studio</h3>
              <p>Derived Historical Dataset Ingestion Hub & Provenance Transparency</p>
            </div>
          </div>
          <button type="button" className="btn-close-modal" onClick={onClose} aria-label="Close modal">
            ✕
          </button>
        </div>

        {message && (
          <div className={`dataset-alert-banner ${message.type}`}>
            {message.type === 'success' ? '✅ ' : '⚠️ '} {message.text}
          </div>
        )}

        {uploadProgress && (
          <div className="upload-progress-banner font-mono">
            ⏳ {uploadProgress}
          </div>
        )}

        {/* Provenance & Source Transparency Card */}
        <div style={{ padding: '16px 24px 0 24px' }}>
          <div
            id="dataset-provenance-panel"
            style={{
              background: 'rgba(15, 23, 42, 0.75)',
              border: '1px solid rgba(56, 139, 253, 0.3)',
              borderRadius: '10px',
              padding: '14px 16px',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px', flexWrap: 'wrap', gap: '6px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontSize: '0.85rem', fontWeight: 700, color: '#f0f6fc' }}>
                  {prov?.dataset_name || 'FieldIQ Derived Historical T20I Deliveries'}
                </span>
                <span style={{ fontSize: '0.7rem', background: 'rgba(56, 139, 253, 0.2)', color: '#58a6ff', padding: '2px 6px', borderRadius: '4px', border: '1px solid #388bfd' }}>
                  v{prov?.dataset_version || '2.0.0'}
                </span>
              </div>
              <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                <span style={{ fontSize: '0.68rem', background: 'rgba(217, 119, 6, 0.2)', color: '#fbbf24', padding: '2px 6px', borderRadius: '4px', border: '1px solid #d97706' }}>
                  Derived historical dataset
                </span>
                <span style={{ fontSize: '0.68rem', background: 'rgba(16, 185, 129, 0.15)', color: '#34d399', padding: '2px 6px', borderRadius: '4px', border: '1px solid #059669' }}>
                  Direction recorded; distance not measured
                </span>
                <span style={{ fontSize: '0.68rem', background: 'rgba(139, 92, 246, 0.2)', color: '#c084fc', padding: '2px 6px', borderRadius: '4px', border: '1px solid #7c3aed' }}>
                  Decision-support output
                </span>
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '10px', fontSize: '0.78rem', color: '#94a3b8', margin: '10px 0' }}>
              <div>
                <strong style={{ color: '#cbd5e1' }}>Primary Spatial Source:</strong>{' '}
                <span style={{ color: '#58a6ff' }}>{prov?.primary_source_repository || 'rishsriv/t20i_data'}</span>
                <div style={{ fontSize: '0.72rem', color: '#64748b', marginTop: '2px' }}>
                  ESPNcricinfo-derived wagon wheels (510 T20Is, 2005–2016, sectors 1–8)
                </div>
              </div>
              <div>
                <strong style={{ color: '#cbd5e1' }}>Ball-by-Ball Enrichment:</strong>{' '}
                <span style={{ color: '#34d399' }}>{prov?.ball_by_ball_enrichment_source || 'Cricsheet (CC BY-SA 4.0)'}</span>
                <div style={{ fontSize: '0.72rem', color: '#64748b', marginTop: '2px' }}>
                  Bowler identities, dismissals & match situation (no wagon wheels in raw Cricsheet)
                </div>
              </div>
            </div>

            {/* Spatial Coverage Breakdown */}
            <div style={{ display: 'flex', justifyContent: 'space-between', background: 'rgba(30, 41, 59, 0.6)', padding: '6px 12px', borderRadius: '6px', fontSize: '0.75rem', marginTop: '8px' }}>
              <span>
                Valid Directional Deliveries (Zone 1–8): <strong style={{ color: '#34d399' }}>{prov?.valid_directional_count?.toLocaleString() || '8,335'} (79.7%)</strong>
              </span>
              <span>
                Spatial Data Unavailable (Zone 0): <strong style={{ color: '#fbbf24' }}>{prov?.zone_0_count?.toLocaleString() || '2,119'} (20.3%)</strong>
              </span>
            </div>

            <div style={{ marginTop: '8px', fontSize: '0.72rem', color: '#94a3b8', lineHeight: 1.4 }}>
              <em>Note: Direction is inherited from the source wagon-wheel sector field (1-8). Distance bands (Inner/Mid/Deep) are categorical proxies derived from runs scored off the bat and must not be interpreted as exact fielder distances. Missing directions (Zone 0) are strictly excluded from spatial danger calculations.</em>
            </div>
          </div>
        </div>

        {/* Dropzone */}
        <div
          className={`dataset-dropzone ${isDragOver ? 'dragover' : ''} ${uploading ? 'uploading' : ''}`}
          onDragOver={(e) => {
            e.preventDefault();
            setIsDragOver(true);
          }}
          onDragLeave={() => setIsDragOver(false)}
          onDrop={(e) => {
            e.preventDefault();
            setIsDragOver(false);
            if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
              handleFilesUpload(e.dataTransfer.files);
            }
          }}
        >
          {/* Multiple Files Picker */}
          <input
            type="file"
            ref={fileInputRef}
            style={{ display: 'none' }}
            multiple
            accept=".csv,.json,.zip"
            onChange={(e) => {
              if (e.target.files && e.target.files.length > 0) {
                handleFilesUpload(e.target.files);
              }
            }}
          />

          {/* Folder Directory Picker */}
          <input
            type="file"
            ref={folderInputRef}
            style={{ display: 'none' }}
            // @ts-ignore
            webkitdirectory=""
            directory=""
            multiple
            onChange={(e) => {
              if (e.target.files && e.target.files.length > 0) {
                handleFilesUpload(e.target.files);
              }
            }}
          />

          <div className="dropzone-content">
            <div className="upload-icon-pulse">📁</div>
            <h4>{uploading ? 'Ingesting, Merging & Profiling Match Deliveries...' : 'Drag & Drop Folder or Files Here'}</h4>
            <p>Supports <strong>Folders of JSONs</strong>, <strong>.zip Archives</strong>, and <strong>.csv Deliveries</strong></p>
            
            <div className="browse-actions-row">
              <button
                type="button"
                className="btn btn-browse"
                onClick={() => fileInputRef.current?.click()}
                disabled={uploading}
              >
                📄 Select Files (.csv, .json, .zip)
              </button>
              <button
                type="button"
                className="btn btn-folder"
                onClick={() => folderInputRef.current?.click()}
                disabled={uploading}
              >
                📁 Select Entire Folder
              </button>
            </div>
          </div>
        </div>

        {/* Telemetry Dashboard */}
        <div className="dataset-telemetry-grid">
          <div className="telemetry-card">
            <span className="telemetry-val font-mono">{summary ? summary.total_deliveries.toLocaleString() : '0'}</span>
            <span className="telemetry-label">Deliveries Ingested</span>
          </div>
          <div className="telemetry-card">
            <span className="telemetry-val font-mono">{summary ? summary.total_matches.toLocaleString() : '0'}</span>
            <span className="telemetry-label">Matches Indexed</span>
          </div>
          <div className="telemetry-card">
            <span className="telemetry-val font-mono">{summary ? summary.unique_batters_count : '0'}</span>
            <span className="telemetry-label">Batters Discovered</span>
          </div>
          <div className="telemetry-card">
            <span className="telemetry-val font-mono">{summary ? summary.unique_bowlers_count : '0'}</span>
            <span className="telemetry-label">Bowlers Profiled</span>
          </div>
          <div className="telemetry-card" id="telemetry-missing-zones">
            <span className="telemetry-val font-mono" style={{ color: '#fbbf24' }}>
              {summary?.missing_zone_deliveries ? summary.missing_zone_deliveries.toLocaleString() : '2,119'}
            </span>
            <span className="telemetry-label">Zone 0 Missing (Unavailable)</span>
          </div>
        </div>

        {/* Action Footer */}
        <div className="dataset-modal-footer">
          <div className="last-sync-time">
            {summary?.last_updated && (
              <span className="font-mono">Last Synced: {new Date(summary.last_updated).toLocaleTimeString()}</span>
            )}
          </div>
          <div className="footer-btns">
            <button
              type="button"
              className="btn btn-retrain"
              onClick={handleRetrain}
              disabled={loading || uploading}
            >
              ⚡ Retrain Models & Refresh Roster
            </button>
            <button type="button" className="btn btn-done" onClick={onClose}>
              Done
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
