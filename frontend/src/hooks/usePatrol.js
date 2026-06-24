import { useEffect } from "react";
import { simulatePatrol } from "../api/patrol";
import { useDebouncedValue, useMutation } from "./useFetch";

/**
 * usePatrol — debounces `teams` and calls POST /api/patrol/simulate, which
 * runs the real MILP solver (or its internal greedy fallback) server-side.
 */
export function usePatrol(teams) {
  const debouncedTeams = useDebouncedValue(teams, 350);
  const { data, loading, error, mutate } = useMutation((n, signal) => simulatePatrol(n, signal));

  useEffect(() => {
    mutate(debouncedTeams).catch(() => {
      /* surfaced via `error` */
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedTeams]);

  return { result: data, loading, error };
}

