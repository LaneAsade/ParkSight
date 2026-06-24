/**
 * src/types/api.js — JSDoc type definitions for backend response shapes.
 * Mirrors backend/app/schemas.py. Plain JS project (no TypeScript build
 * step), so these exist purely for editor intellisense via `@type`/`@param`
 * JSDoc annotations — nothing here is imported at runtime.
 */

/**
 * @typedef {"REAL_DATA"|"MODELED"|"PARTIAL"|"SPEC_ONLY"} EvidenceStatus
 * @typedef {"CRITICAL"|"HIGH"|"MEDIUM"|"LOW"} RiskTier
 */

/**
 * @typedef {Object} Hotspot
 * @property {number} cluster_id
 * @property {string|null} top_junction
 * @property {string|null} district
 * @property {number|null} violations
 * @property {number|null} risk_score
 * @property {RiskTier|null} risk_tier
 * @property {number|null} congestion_index
 * @property {EvidenceStatus|null} traffic_validation_status
 */

/**
 * @typedef {Object} ApiErrorPayload
 * @property {string} code
 * @property {string} message
 * @property {string|null} artifact
 * @property {boolean|null} required
 */

export {};
