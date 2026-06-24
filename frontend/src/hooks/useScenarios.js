import { simulateScenario } from "../api/scenarios";
import { useMutation } from "./useFetch";

export function useScenarioSimulation() {
  return useMutation((body, signal) => simulateScenario(body, signal));
}
