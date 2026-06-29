import { apiGet, apiPost } from "./client";

export const getCurrentPatrol = (signal) => apiGet("/patrol/current", null, signal);

export const simulatePatrol = (teams, signal) => apiPost("/patrol/simulate", { teams }, signal);