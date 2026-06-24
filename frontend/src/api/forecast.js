import { apiGet } from "./client";

export const getForecastSummary = (signal) => apiGet("/forecast/summary", null, signal);

export const getForecastForCluster = (clusterId, signal) => apiGet(`/forecast/${clusterId}`, null, signal);

