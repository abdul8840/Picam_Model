import React from 'react';
import { format, addDays, subDays } from 'date-fns';
import './DatePicker.css';

function DatePicker({ value, onChange }) {
  const handlePrevDay = () => {
    onChange(subDays(value, 1));
  };

  const handleNextDay = () => {
    const tomorrow = addDays(new Date(), 1);
    if (addDays(value, 1) < tomorrow) {
      onChange(addDays(value, 1));
    }
  };

  const handleDateChange = (e) => {
    onChange(new Date(e.target.value));
  };

  const isToday = format(value, 'yyyy-MM-dd') === format(new Date(), 'yyyy-MM-dd');

  return (
    <div className="date-picker">
      <button 
        className="date-picker-btn"
        onClick={handlePrevDay}
        title="Previous day"
      >
        ←
      </button>
      
      <div className="date-picker-display">
        <input
          type="date"
          value={format(value, 'yyyy-MM-dd')}
          onChange={handleDateChange}
          max={format(new Date(), 'yyyy-MM-dd')}
          className="date-input"
        />
        <span className="date-text">
          {format(value, 'EEE, MMM d, yyyy')}
        </span>
      </div>
      
      <button 
        className="date-picker-btn"
        onClick={handleNextDay}
        disabled={isToday}
        title="Next day"
      >
        →
      </button>
    </div>
  );
}

export default DatePicker;