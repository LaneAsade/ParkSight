import { getCongestionSummary, getCongestionByDistrict, getCongestionRelationship } from "../api/congestion";
import { useFetch } from "./useFetch";

export function useCongestionSummary() {
  return useFetch((signal) => getCongestionSummary(signal), []);
}

export function useCongestionByDistrict() {
  return useFetch((signal) => getCongestionByDistrict(signal), []);
}

export function useCongestionRelationship() {
  return useFetch((signal) => getCongestionRelationship(signal), []);
}
