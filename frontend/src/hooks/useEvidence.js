import { useMemo } from "react";
import { getEvidence, getEvidenceSummary } from "../api/evidence";
import { useFetch } from "./useFetch";

export function useEvidence(filters = {}) {
  const key = useMemo(() => JSON.stringify(filters), [filters]);
  return useFetch((signal) => getEvidence(filters, signal), [key]);
}

export function useEvidenceSummary() {
  return useFetch((signal) => getEvidenceSummary(signal), []);
}
