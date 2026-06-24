import { getHotspot } from "../api/hotspots";
import { useFetch } from "./useFetch";

export function useHotspotDetail(clusterId) {
  return useFetch(
    (signal) => (clusterId == null ? Promise.resolve(null) : getHotspot(clusterId, signal)),
    [clusterId]
  );
}

