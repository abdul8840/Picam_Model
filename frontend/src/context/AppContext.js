import React, { createContext, useContext, useState, useCallback } from 'react';
import { format, subDays } from 'date-fns';

const AppContext = createContext();

export function AppProvider({ children }) {
  const [selectedDate, setSelectedDate] = useState(new Date());
  const [dateRange, setDateRange] = useState({
    start: subDays(new Date(), 7),
    end: new Date()
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [notifications, setNotifications] = useState([]);

  const formatDate = useCallback((date) => {
    return format(date, 'yyyy-MM-dd');
  }, []);

  const addNotification = useCallback((message, type = 'info') => {
    const id = Date.now();
    setNotifications(prev => [...prev, { id, message, type }]);
    setTimeout(() => {
      setNotifications(prev => prev.filter(n => n.id !== id));
    }, 5000);
  }, []);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const value = {
    selectedDate,
    setSelectedDate,
    dateRange,
    setDateRange,
    loading,
    setLoading,
    error,
    setError,
    clearError,
    notifications,
    addNotification,
    formatDate
  };

  return (
    <AppContext.Provider value={value}>
      {children}
    </AppContext.Provider>
  );
}

export function useApp() {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp must be used within AppProvider');
  }
  return context;
}

export default AppContext;