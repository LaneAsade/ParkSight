import { apiGet, apiPost } from "./client";

export const getSystemStatus = (signal) => apiGet("/system/status", null, signal);

export const getSystemConfig = (signal) => apiGet("/system/config", null, signal);

export const getSystemRuns = (signal) => apiGet("/system/runs", null, signal);

export const reloadSystem = (signal) => apiPost("/system/reload", undefined, signal);

