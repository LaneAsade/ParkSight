import { apiGet } from "./client";

export const getEvidence = (filters = {}, signal) => apiGet("/evidence", filters, signal);

export const getEvidenceSummary = (signal) => apiGet("/evidence/summary", null, signal);

