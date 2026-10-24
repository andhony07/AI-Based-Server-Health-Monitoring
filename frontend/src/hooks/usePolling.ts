import { useCallback, useEffect, useRef } from 'react';

interface UsePollingOptions {
  enabled?: boolean;
  intervalMs?: number;
  runImmediately?: boolean;
}

export function usePolling(
  callback: () => Promise<void> | void,
  options: UsePollingOptions = {}
) {
  const { enabled = true, intervalMs = 5000, runImmediately = true } = options;
  const isExecutingRef = useRef(false);
  const savedCallback = useRef(callback);

  useEffect(() => {
    savedCallback.current = callback;
  }, [callback]);

  const execute = useCallback(async () => {
    if (isExecutingRef.current) return;
    try {
      isExecutingRef.current = true;
      await savedCallback.current();
    } finally {
      isExecutingRef.current = false;
    }
  }, []);

  useEffect(() => {
    if (!enabled) return;

    if (runImmediately) {
      execute();
    }

    const timer = setInterval(() => {
      execute();
    }, intervalMs);

    return () => {
      clearInterval(timer);
    };
  }, [enabled, intervalMs, runImmediately, execute]);

  return { execute };
}
