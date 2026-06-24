import { getSystemStatus } from "../api/system";
import { useFetch } from "./useFetch";

export function useSystemStatus() {
  return useFetch((signal) => getSystemStatus(signal), []);
}

