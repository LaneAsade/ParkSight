import { apiPost } from "./client";

export const queryCopilot = (query, signal) => apiPost("/copilot/query", { query }, signal);

