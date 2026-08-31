import React, { useState, useEffect, useRef } from 'react';
import './DatasetStudioModal.css';

interface DatasetSummary {
  status: string;
  total_deliveries: number;
  total_matches: number;
  unique_batters_count: number;
  unique_bowlers_count: number;
  batters: string[];
  bowlers: string[];
  last_updated: string;
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

  return (
    <div className="dataset-modal-backdrop" onClick={onClose}>
      <div className="dataset-modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="dataset-modal-header">
          <div className="header-brand">
            <span className="hub-icon">📂</span>
            <div>
              <h3>Real-Life Dataset Studio</h3>
              <p>Batch ingest folders of Cricsheet JSON matches, .zip archives, or CSV delivery logs into FieldIQ ML</p>
            </div>
          </div>
          <button type="button" className="btn-close-modal" onClick={onClose}>
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
