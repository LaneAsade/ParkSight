// frontend/src/pages/OverviewPage.jsx
import { useState, useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import { useOverview } from "../hooks/useOverview";
import { useHotspots } from "../hooks/useHotspots";
import { LoadingState, ErrorState } from "../components/StatusStates";
import { fmtNumber, fmtPercent } from "../utils/format";

// ── Tier colours ─────────────────────────────────────────────────────────────
const TIER_COLOR = {
  CRITICAL: { bg: "#ef4444", ring: "ring-red-500",   label: "bg-red-500/20 text-red-400 border-red-500/40" },
  HIGH:     { bg: "#f97316", ring: "ring-orange-500", label: "bg-orange-500/20 text-orange-400 border-orange-500/40" },
  MEDIUM:   { bg: "#eab308", ring: "ring-yellow-500", label: "bg-yellow-500/20 text-yellow-400 border-yellow-500/40" },
  LOW:      { bg: "#22c55e", ring: "ring-green-500",  label: "bg-green-500/20 text-green-400 border-green-500/40" },
};

// ── KPI Card ──────────────────────────────────────────────────────────────────
function KPI({ label, value, sub, accent }) {
  return (
    <div className={`rounded-xl border px-4 py-3 bg-gray-900 ${accent || "border-gray-800"}`}>
      <div className="text-xs font-mono uppercase tracking-widest text-gray-500 mb-1">{label}</div>
      <div className="text-2xl font-bold text-gray-100">{value ?? "—"}</div>
      {sub && <div className="text-xs text-gray-500 mt-0.5">{sub}</div>}
    </div>
  );
}

// ── Hotspot Sidebar Item ──────────────────────────────────────────────────────
function HotspotRow({ h, onHover, isActive }) {
  const tier = TIER_COLOR[h.risk_tier] || TIER_COLOR.LOW;
  return (
    <Link
      to={`/hotspots/${h.cluster_id}`}
      onMouseEnter={() => onHover(h)}
      onMouseLeave={() => onHover(null)}
      className={`block px-3 py-2.5 rounded-lg border transition-all ${
        isActive
          ? "bg-amber-400/10 border-amber-400/40"
          : "border-transparent hover:bg-gray-800/60 hover:border-gray-700"
      }`}
    >
      <div className="flex items-center justify-between gap-2 mb-0.5">
        <span className="text-sm font-medium text-gray-100 truncate">{h.top_junction}</span>
        <span className={`text-xs px-1.5 py-0.5 rounded border font-mono shrink-0 ${tier.label}`}>
          {h.risk_tier}
        </span>
      </div>
      <div className="text-xs text-gray-500 flex gap-3">
        <span>{fmtNumber(h.violations)} violations</span>
        {h.capacity_loss_pct != null && (
          <span className="text-red-400">{fmtPercent(h.capacity_loss_pct)} cap. loss</span>
        )}
      </div>
    </Link>
  );
}

// ── Leaflet Map (lazy-loaded) ─────────────────────────────────────────────────
function BengaluruMap({ hotspots, activeHotspot }) {
  const mapRef = useRef(null);
  const leafletMapRef = useRef(null);
  const markersRef = useRef([]);

  useEffect(() => {
    // Dynamically import leaflet to avoid SSR issues
    import("leaflet").then((L) => {
      if (leafletMapRef.current) return; // already initialised

      const map = L.map(mapRef.current, {
        center: [12.9716, 77.5946],
        zoom: 12,
        zoomControl: true,
      });

      L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
        attribution: "© OpenStreetMap contributors © CARTO",
        subdomains: "abcd",
        maxZoom: 19,
      }).addTo(map);

      leafletMapRef.current = map;
    });

    return () => {
      if (leafletMapRef.current) {
        leafletMapRef.current.remove();
        leafletMapRef.current = null;
      }
    };
  }, []);

  // Update markers when hotspots change
  useEffect(() => {
    if (!leafletMapRef.current || !hotspots?.length) return;
    import("leaflet").then((L) => {
      // Clear old markers
      markersRef.current.forEach((m) => m.remove());
      markersRef.current = [];

      hotspots.forEach((h) => {
        if (h.lat==null||h.lon==null) return;
        const color = TIER_COLOR[h.risk_tier]?.bg || "#22c55e";
        const isActive = activeHotspot?.cluster_id === h.cluster_id;

        const icon = L.divIcon({
          className: "",
          html: `<div style="
            width:${isActive ? 18 : 12}px;
            height:${isActive ? 18 : 12}px;
            border-radius:50%;
            background:${color};
            border:2px solid ${isActive ? "#fff" : color}88;
            box-shadow:0 0 ${isActive ? 12 : 6}px ${color}99;
            transition:all 0.2s;
          "></div>`,
          iconSize: [isActive ? 18 : 12, isActive ? 18 : 12],
          iconAnchor: [isActive ? 9 : 6, isActive ? 9 : 6],
        });

        const marker = L.marker([h.lat, h.lon], { icon })
          .addTo(leafletMapRef.current)
          .bindPopup(`
            <div style="font-family:monospace;font-size:12px;min-width:180px">
              <strong style="color:#f59e0b">${h.top_junction || "Cluster " + h.cluster_id}</strong><br/>
              <span style="color:#9ca3af">${h.police_station || ""}</span><br/>
              <hr style="border-color:#374151;margin:6px 0"/>
              Tier: <strong style="color:${color}">${h.risk_tier}</strong><br/>
              Violations: ${fmtNumber(h.violations)}<br/>
              ${h.congestion_index != null ? `Congestion: ${h.congestion_index.toFixed(2)}×<br/>` : ""}
              ${h.capacity_loss_pct != null ? `Cap. loss: ${fmtPercent(h.capacity_loss_pct)}<br/>` : ""}
              <a href="/hotspots/${h.cluster_id}" style="color:#f59e0b">View details →</a>
            </div>
          `, { maxWidth: 220 });

        markersRef.current.push(marker);
      });
    });
  }, [hotspots, activeHotspot]);

  return (
    <div
      ref={mapRef}
      className="w-full h-full rounded-xl overflow-hidden"
      style={{ minHeight: 400 }}
    />
  );
}

// ── Main Command Center ───────────────────────────────────────────────────────
export default function OverviewPage() {
  const { data: overview, loading: oLoading, error: oError } = useOverview();
  const { data: hotspotsData, loading: hLoading } = useHotspots({ risk_tier: undefined });
  const [activeHotspot, setActiveHotspot] = useState(null);
  const [tierFilter, setTierFilter] = useState("ALL");

  const allHotspots = hotspotsData?.items || [];
  const filtered = tierFilter === "ALL"
    ? allHotspots
    : allHotspots.filter((h) => h.risk_tier === tierFilter);

  const criticalCount = allHotspots.filter((h) => h.risk_tier === "CRITICAL").length;
  const avgCapLoss = allHotspots.reduce((s, h) => s + (h.capacity_loss_pct || 0), 0) /
    (allHotspots.length || 1);
  const meanCongestion = overview?.mean_congestion_index;
  const patrolCoverage = overview?.patrol_coverage_pct;

  if (oLoading || hLoading) return <LoadingState label="Loading command center…" />;
  if (oError) return <ErrorState error={oError} />;

  return (
    <div className="flex flex-col h-screen bg-gray-950">
      {/* ── Top bar ── */}
      <div className="shrink-0 px-4 pt-3 pb-2 border-b border-gray-800 bg-gray-900/80 backdrop-blur">
        <div className="flex items-center justify-between mb-2">
          <h1 className="text-sm font-mono uppercase tracking-widest text-amber-400 font-semibold">
            Traffic Command Center — Bengaluru
          </h1>
          <span className="text-xs font-mono text-gray-500">
            {new Date().toLocaleTimeString("en-IN")} IST · Live
          </span>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
          <KPI
            label="Critical Zones"
            value={criticalCount}
            sub="require immediate action"
            accent="border-red-800/60"
          />
          <KPI
            label="Avg Capacity Loss"
            value={fmtPercent(avgCapLoss)}
            sub="across all hotspots"
            accent="border-orange-800/60"
          />
          <KPI
            label="Congestion Index"
            value={meanCongestion != null ? meanCongestion.toFixed(2) + "×" : "—"}
            sub="free-flow baseline"
            accent="border-yellow-800/60"
          />
          <KPI
            label="Patrol Coverage"
            value={fmtPercent(patrolCoverage)}
            sub={overview?.patrol_teams_used ? `${overview.patrol_teams_used} teams` : undefined}
            accent="border-blue-800/60"
          />
          <KPI
            label="Hotspot Clusters"
            value={fmtNumber(overview?.n_hotspot_clusters)}
            sub={`${overview?.active_districts || 0} active districts`}
          />
        </div>
      </div>

      {/* ── Map + Sidebar ── */}
      <div className="flex-1 flex min-h-0">
        {/* Map — 75% width */}
        <div className="flex-1 relative p-2">
          {/* Layer toggles */}
          <div className="absolute top-4 left-4 z-[1000] flex gap-1.5 flex-wrap">
            {["ALL", "CRITICAL", "HIGH", "MEDIUM", "LOW"].map((t) => (
              <button
                key={t}
                onClick={() => setTierFilter(t)}
                className={`text-xs px-2.5 py-1 rounded-full border font-mono transition-all backdrop-blur-sm ${
                  tierFilter === t
                    ? "bg-amber-400 text-gray-950 border-amber-400 font-bold"
                    : "bg-gray-900/80 text-gray-400 border-gray-700 hover:border-gray-500"
                }`}
              >
                {t}
              </button>
            ))}
          </div>

          {/* Legend */}
          <div className="absolute bottom-4 left-4 z-[1000] bg-gray-900/90 border border-gray-700 rounded-xl px-3 py-2 backdrop-blur-sm">
            <div className="text-xs font-mono text-gray-500 mb-1.5 uppercase tracking-widest">Impact Tier</div>
            {Object.entries(TIER_COLOR).map(([tier, { bg }]) => (
              <div key={tier} className="flex items-center gap-2 text-xs text-gray-300 mb-1">
                <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ background: bg }} />
                {tier}
              </div>
            ))}
          </div>

          <BengaluruMap hotspots={filtered} activeHotspot={activeHotspot} />
        </div>

        {/* Sidebar — 25% width, scrollable */}
        <div className="w-72 shrink-0 border-l border-gray-800 bg-gray-900 flex flex-col">
          <div className="px-3 py-2.5 border-b border-gray-800 flex items-center justify-between">
            <span className="text-xs font-mono uppercase tracking-widest text-gray-500">
              Hotspots ({filtered.length})
            </span>
            <Link
              to="/hotspots"
              className="text-xs text-amber-400 hover:text-amber-300"
            >
              View all →
            </Link>
          </div>
          <div className="flex-1 overflow-y-auto p-2 space-y-1">
            {filtered.length === 0 && (
              <div className="text-sm text-gray-600 p-4 text-center">
                No hotspots match this filter.
              </div>
            )}
            {filtered
              .slice()
              .sort((a, b) => (b.risk_score || 0) - (a.risk_score || 0))
              .map((h) => (
                <HotspotRow
                  key={h.cluster_id}
                  h={h}
                  onHover={setActiveHotspot}
                  isActive={activeHotspot?.cluster_id === h.cluster_id}
                />
              ))}
          </div>
          {/* Quick actions */}
          <div className="p-3 border-t border-gray-800 space-y-2">
            <Link
              to="/scenarios"
              className="flex items-center justify-center gap-2 w-full py-2 rounded-lg bg-gray-800 border border-gray-700 text-gray-300 text-sm hover:bg-gray-700 transition-colors"
            >
              🧪 Run Scenario
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}