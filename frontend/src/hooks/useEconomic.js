import { getEconomicAssumptions, simulateEconomic } from "../api/economic";
import { useFetch } from "./useFetch";
import { useMutation } from "./useFetch";

export function useEconomicAssumptions() {
  return useFetch((signal) => getEconomicAssumptions(signal), []);
}

export function useEconomicSimulation() {
  return useMutation((body, signal) => simulateEconomic(body, signal));
}
