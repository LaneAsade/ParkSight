import { getOverview } from "../api/overview";
import { useFetch } from "./useFetch";

export function useOverview() {
  return useFetch((signal) => getOverview(signal), []);
}

