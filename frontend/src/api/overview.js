import { apiGet } from "./client";

export const getOverview = (signal) => apiGet("/overview", null, signal);

