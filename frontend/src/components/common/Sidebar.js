import React from 'react';
import { NavLink } from 'react-router-dom';
import './Sidebar.css';

const menuItems = [
  { path: '/dashboard', label: 'Dashboard', icon: '📊' },
  { path: '/metrics', label: 'Metrics', icon: '📈' },
  { path: '/insights', label: 'Insights', icon: '💡' },
  { path: '/roi', label: 'ROI Log', icon: '💰' },
  { path: '/settings', label: 'Settings', icon: '⚙️' }
];

function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="sidebar-logo">
          <span className="logo-icon">⚡</span>
          <span className="logo-text">PICAM</span>
        </div>
      </div>
      
      <nav className="sidebar-nav">
        {menuItems.map(item => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) => 
              `nav-item ${isActive ? 'active' : ''}`
            }
          >
            <span className="nav-icon">{item.icon}</span>
            <span className="nav-label">{item.label}</span>
          </NavLink>
        ))}
      </nav>
      
      <div className="sidebar-footer">
        <div className="sidebar-info">
          <div className="info-label">Physics Engine</div>
          <div className="info-value">v1.0.0</div>
        </div>
        <div className="sidebar-info">
          <div className="info-label">Mode</div>
          <div className="info-value">Deterministic</div>
        </div>
      </div>
    </aside>
  );
}

export default Sidebar;