import { useState, useCallback } from 'react';
import { subDays, addDays, format } from 'date-fns';

export function useDateRange(initialDays = 7) {
  const [dateRange, setDateRange] = useState({
    start: subDays(new Date(), initialDays - 1),
    end: new Date()
  });

  const setRange = useCallback((start, end) => {
    setDateRange({ start, end });
  }, []);

  const setLastNDays = useCallback((days) => {
    setDateRange({
      start: subDays(new Date(), days - 1),
      end: new Date()
    });
  }, []);

  const shiftRange = useCallback((days) => {
    setDateRange(prev => ({
      start: addDays(prev.start, days),
      end: addDays(prev.end, days)
    }));
  }, []);

  const formatRange = useCallback(() => {
    return {
      start: format(dateRange.start, 'yyyy-MM-dd'),
      end: format(dateRange.end, 'yyyy-MM-dd')
    };
  }, [dateRange]);

  const daysInRange = Math.ceil(
    (dateRange.end - dateRange.start) / (1000 * 60 * 60 * 24)
  ) + 1;

  return {
    dateRange,
    setRange,
    setLastNDays,
    shiftRange,
    formatRange,
    daysInRange
  };
}

export default useDateRange;