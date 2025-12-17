import { useState, useEffect } from 'react';

export const useDreamMode = (timeoutMs: number = 300000) => {
  const [isDreaming, setIsDreaming] = useState(false);

  useEffect(() => {
    let timeout: NodeJS.Timeout;

    const resetTimer = () => {
      if (isDreaming) setIsDreaming(false);
      clearTimeout(timeout);
      timeout = setTimeout(() => setIsDreaming(true), timeoutMs);
    };

    window.addEventListener('mousemove', resetTimer);
    window.addEventListener('keydown', resetTimer);
    window.addEventListener('click', resetTimer);
    window.addEventListener('scroll', resetTimer);

    // Initial start
    resetTimer();

    return () => {
      clearTimeout(timeout);
      window.removeEventListener('mousemove', resetTimer);
      window.removeEventListener('keydown', resetTimer);
      window.removeEventListener('click', resetTimer);
      window.removeEventListener('scroll', resetTimer);
    };
  }, [timeoutMs, isDreaming]); // Added isDreaming dependency to avoid setting state redundant

  return isDreaming;
};
