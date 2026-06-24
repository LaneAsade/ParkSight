import { queryCopilot } from "../api/copilot";
import { useMutation } from "./useFetch";

export function useCopilot() {
  return useMutation((query, signal) => queryCopilot(query, signal));
}
