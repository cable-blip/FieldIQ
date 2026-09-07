import React, { useState } from 'react';
import './Navbar.css';

interface NavbarProps {
  onOpenDatasetStudio: () => void;
  onResetLayout: () => void;
  onCopyCoordinates?: () => void;
  venueName?: string;
  isGameplanActive?: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({
  onOpenDatasetStudio,
  onResetLayout,
  onCopyCoordinates,
  venueName = "Lord's",
  isGameplanActive = false
}) => {
  const [copied, setCopied] = useState<boolean>(false);

  const handleCopy = () => {
    if (onCopyCoordinates) {
      onCopyCoordinates();
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <header className="navbar-container">
      <div className="navbar-left">
        <div className="brand-logo-gem">
          <span className="brand-icon">⚡</span>
        </div>
        <div className="brand-header">
          <div className="brand-title-wrap">
            <span className="brand-title font-display">FIELDIQ</span>
            <span className="brand-badge font-mono">PRO 3.0</span>
          </div>
          <span className="brand-sub font-mono">CYBERNETIC SPATIAL INTELLIGENCE</span>
        </div>
      </div>

      <div className="navbar-center">
        <div className="live-status-pill">
          <span className="pulse-dot" />
          <span className="status-text font-mono">
            {isGameplanActive ? 'MULTI-OVER SEQUENCING ACTIVE' : 'LIVE 1,000-DELIVERY MONTE CARLO'} · {venueName.toUpperCase()}
          </span>
        </div>
      </div>

      <div className="navbar-right">
        {onCopyCoordinates && (
          <button
            type="button"
            className="btn-nav-action copy-btn font-mono"
            onClick={handleCopy}
            title="Copy 3D fielder coordinates to clipboard"
          >
            {copied ? '✅ COPIED' : '📋 COPY COORDS'}
          </button>
        )}

        <button
          type="button"
          className="btn-nav-action dataset-studio-btn font-mono"
          onClick={onOpenDatasetStudio}
        >
          📂 DATASET STUDIO
        </button>

        <button
          type="button"
          className="btn-nav-action reset-btn font-mono"
          onClick={onResetLayout}
          title="Reset field positions to standard default"
        >
          🔄 RESET
        </button>
      </div>
    </header>
  );
};
