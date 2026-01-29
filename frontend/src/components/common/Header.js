import React from 'react';
import { useApp } from '../../context/AppContext';
import DatePicker from './DatePicker';
import './Header.css';

function Header() {
  const { selectedDate, setSelectedDate } = useApp();

  return (
    <header className="header">
      <div className="header-left">
        <h1 className="header-title">PICAM Dashboard</h1>
        <span className="header-subtitle">Physics-based Loss Detection</span>
      </div>
      
      <div className="header-right">
        <DatePicker
          value={selectedDate}
          onChange={setSelectedDate}
        />
        
        <div className="header-status">
          <span className="status-dot"></span>
          <span>System Active</span>
        </div>
      </div>
    </header>
  );
}

export default Header;