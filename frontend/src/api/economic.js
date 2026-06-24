import { apiGet, apiPost } from "./client";

export const getEconomicAssumptions = (signal) => apiGet("/economic/assumptions", null, signal);

export const simulateEconomic = (body, signal) => apiPost("/economic/simulate", body, signal);

