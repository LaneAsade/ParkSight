/**
 * src/utils/format.js — shared display formatters. Centralized so every
 * page renders missing data ("—") the same way instead of each component
 * inventing its own placeholder.
 */

const DASH = "—";

export function fmtNumber(value, opts = {}) {
  if (value === null || value === undefined || Number.isNaN(value)) return DASH;
  return new Intl.NumberFormat("en-IN", opts).format(value);
}

export function fmtPercent(value, digits = 1) {
  if (value === null || value === undefined || Number.isNaN(value)) return DASH;
  return `${value.toFixed(digits)}%`;
}

export function fmtInr(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return DASH;
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(value);
}

export function fmtDate(iso) {
  if (!iso) return DASH;
  try {
    return new Intl.DateTimeFormat("en-IN", {
      year: "numeric",
      month: "short",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

export function fmtOrDash(value, suffix = "") {
  if (value === null || value === undefined || value === "") return DASH;
  return `${value}${suffix}`;
}

export const PLACEHOLDER = DASH;
