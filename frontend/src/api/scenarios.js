import { apiPost } from "./client";

export const simulateScenario = (body, signal) => apiPost("/scenarios/simulate", body, signal);

