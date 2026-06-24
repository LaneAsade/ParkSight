import { apiGet } from "./client";

export const getHotspots = (filters = {}, signal) => apiGet("/hotspots", filters, signal);

export const getHotspot = (clusterId, signal) => apiGet(`/hotspots/${clusterId}`, null, signal);

export const getNonJunctionHotspots = (signal) => apiGet("/nonjunction-hotspots", null, signal);

