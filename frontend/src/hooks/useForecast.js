import { getForecastSummary, getForecastForCluster } from "../api/forecast";
import { useFetch } from "./useFetch";

export function useForecastSummary() {
  return useFetch((signal) => getForecastSummary(signal), []);
}

export function useForecastForCluster(clusterId) {
  return useFetch(
    (signal) => (clusterId == null ? Promise.resolve(null) : getForecastForCluster(clusterId, signal)),
    [clusterId]
  );
}
