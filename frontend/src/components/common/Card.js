import React from 'react';
import './Card.css';

function Card({ 
  title, 
  subtitle, 
  children, 
  className = '', 
  headerAction,
  loading = false 
}) {
  return (
    <div className={`card ${className}`}>
      {(title || headerAction) && (
        <div className="card-header">
          <div className="card-header-text">
            {title && <h3 className="card-title">{title}</h3>}
            {subtitle && <p className="card-subtitle">{subtitle}</p>}
          </div>
          {headerAction && (
            <div className="card-header-action">
              {headerAction}
            </div>
          )}
        </div>
      )}
      <div className={`card-body ${loading ? 'loading' : ''}`}>
        {loading ? (
          <div className="card-loading">
            <div className="spinner"></div>
          </div>
        ) : (
          children
        )}
      </div>
    </div>
  );
}

export default Card;