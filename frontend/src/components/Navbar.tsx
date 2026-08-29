import React from 'react';
import './Navbar.css';

interface NavbarProps {
  onOpenDatasetStudio: () => void;
  onResetLayout?: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  onOpenDatasetStudio,
  onResetLayout
}) => {
  return (
    <header className="navbar-container">
      <div className="navbar-brand">
        <div className="brand-logo-gem">🏏</div>
        <div className="brand-text">
          <span className="brand-title">FIELDIQ</span>
          <span className="brand-badge">PRO</span>
        </div>
        <span className="brand-sub">Tactical Intelligence Suite</span>
      </div>

      <div className="navbar-center">
        <div className="live-status-pill">
          <span className="pulse-dot" />
          <span className="status-text">Bayesian ML & 1,000-Delivery Monte Carlo Active</span>
        </div>
      </div>

      <div className="navbar-actions">
        <button
          type="button"
          className="btn-nav-action dataset-studio-btn"
          onClick={onOpenDatasetStudio}
        >
          📂 Dataset Studio Hub
        </button>

        {onResetLayout && (
          <button
            type="button"
            className="btn-nav-action reset-btn"
            onClick={onResetLayout}
            title="Reset standard field layout"
          >
            🔄 Reset
          </button>
        )}
      </div>
    </header>
  );
};
