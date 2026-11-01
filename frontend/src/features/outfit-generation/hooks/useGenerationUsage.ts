import { useCallback, useEffect, useState } from 'react';
import { getGenerationUsage } from '../api/generation.api';
import type { IGenerationUsage } from '../api/generation.api';

export function useGenerationUsage() {
  const [usage, setUsage] = useState<IGenerationUsage | null>(null);
  const [error, setError] = useState(false);
  const [loading, setLoading] = useState(true);
  const reload = useCallback(async () => {
    setLoading(true);
    setError(false);
    try {
      setUsage(await getGenerationUsage());
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }, []);
  useEffect(() => {
    let active = true;
    const load = async () => {
      try {
        const result = await getGenerationUsage();
        if (active) setUsage(result);
      } catch {
        if (active) setError(true);
      } finally {
        if (active) setLoading(false);
      }
    };
    void load();
    return () => { active = false; };
  }, []);
  return { usage, error, loading, reload };
}

