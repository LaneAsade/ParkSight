/**
 * src/api/client.js — thin fetch wrapper shared by every domain API module.
 *
 * Base URL comes from VITE_API_BASE_URL (see .env.example). No API keys are
 * ever read or sent from the frontend — secrets live only in the backend's
 * environment.
 */

const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api";

export class ApiError extends Error {
  constructor(message, { status, code, artifact, required, payload } = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.artifact = artifact;
    this.required = required;
    this.payload = payload;
  }
}

async function request(path, { method = "GET", body, params, signal } = {}) {
  let url = `${BASE_URL}${path}`;
  if (params) {
    const qs = new URLSearchParams(
      Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== "")
    ).toString();
    if (qs) url += `?${qs}`;
  }

  let response;
  try {
    response = await fetch(url, {
      method,
      headers: body ? { "Content-Type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined,
      signal,
    });
  } catch (networkErr) {
    throw new ApiError(`Network error calling ${path}: ${networkErr.message}`, { status: 0 });
  }

  let payload = null;
  const text = await response.text();
  if (text) {
    try {
      payload = JSON.parse(text);
    } catch {
      payload = { raw: text };
    }
  }

  if (!response.ok) {
    const detail = payload?.detail ?? payload?.error ?? {};
    throw new ApiError(detail.message || `Request to ${path} failed with ${response.status}`, {
      status: response.status,
      code: detail.code,
      artifact: detail.artifact,
      required: detail.required,
      payload,
    });
  }

  return payload;
}

export const apiGet = (path, params, signal) => request(path, { method: "GET", params, signal });
export const apiPost = (path, body, signal) => request(path, { method: "POST", body, signal });

