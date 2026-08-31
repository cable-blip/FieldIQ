import React, { useState } from 'react';
import './Navbar.css';

interface NavbarProps {
  onOpenDatasetStudio: () => void;
  onResetLayout: () => void;
  onCopyCoordinates?: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  onOpenDatasetStudio,
  onResetLayout,
  onCopyCoordinates
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
        <div className="brand-logo-gem">🏏</div>
        <div className="brand-header">
          <div className="brand-title-wrap">
            <span className="brand-title">FIELDIQ</span>
            <span className="brand-badge">PRO</span>
          </div>
          <span className="brand-sub">SPATIAL INTELLIGENCE SUITE</span>
        </div>
      </div>

      <div className="navbar-center">
        <div className="live-status-pill">
          <span className="pulse-dot" />
          <span className="status-text font-mono">LIVE PROBABILITY ENGINE · 1,000-DELIVERY MONTE CARLO ACTIVE</span>
        </div>
      </div>

      <div className="navbar-right">
        {onCopyCoordinates && (
          <button
            type="button"
            className="btn-nav-action copy-btn"
            onClick={handleCopy}
            title="Copy 3D fielder coordinates to clipboard"
          >
            {copied ? '✅ Copied JSON' : '📋 Copy Coords'}
          </button>
        )}

        <button
          type="button"
          className="btn-nav-action dataset-studio-btn"
          onClick={onOpenDatasetStudio}
        >
          📂 Dataset Studio
        </button>

        <button
          type="button"
          className="btn-nav-action reset-btn"
          onClick={onResetLayout}
          title="Reset field positions to standard default"
        >
          🔄 Reset Field
        </button>
      </div>
    </header>
  );
};
