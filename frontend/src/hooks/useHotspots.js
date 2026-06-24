import { useMemo } from "react";
import { getHotspots } from "../api/hotspots";
import { useFetch } from "./useFetch";

/**
 * useHotspots — fetches the hotspot list for the given filters. Filters are
 * sent to the API (not applied client-side), per the integration spec.
 */
export function useHotspots(filters) {
  const key = useMemo(() => JSON.stringify(filters), [filters]);
  return useFetch((signal) => getHotspots(filters, signal), [key]);
}

