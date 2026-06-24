import { apiGet } from "./client";

export const getCongestionSummary = (signal) => apiGet("/congestion/summary", null, signal);

export const getCongestionByDistrict = (signal) => apiGet("/congestion/by-district", null, signal);

export const getHotspotCongestion = (clusterId, signal) => apiGet(`/congestion/hotspots/${clusterId}`, null, signal);

export const getCongestionRelationship = (signal) => apiGet("/congestion/relationship", null, signal);

