import { useCallback, useEffect, useState } from 'react';

export function useResource(loader, dependencies = []) {
  const [state, setState] = useState({ data: null, loading: true, error: null });
  const stableLoader = useCallback(loader, dependencies);

  const load = useCallback(async (signal) => {
    setState((current) => ({ ...current, loading: true, error: null }));
    try {
      const data = await stableLoader(signal);
      if (!signal?.aborted) setState({ data, loading: false, error: null });
      return data;
    } catch (error) {
      if (!signal?.aborted) {
        setState((current) => ({ ...current, loading: false, error }));
      }
      throw error;
    }
  }, [stableLoader]);

  useEffect(() => {
    const controller = new AbortController();
    load(controller.signal).catch(() => {});
    return () => controller.abort();
  }, [load]);

  const reload = useCallback(() => {
    const controller = new AbortController();
    return load(controller.signal);
  }, [load]);

  return { ...state, reload };
}
