import { useParams, Link } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { useHotspotDetail } from "../hooks/useHotspotDetail";
import { PageHeader, Panel } from "../components/Panel";
import RiskTierBadge from "../components/RiskTierBadge";
import EvidenceChip from "../components/EvidenceChip";
import { LoadingState, ErrorState } from "../components/StatusStates";
import { fmtNumber, fmtPercent, fmtOrDash } from "../utils/format";
import { useState, useEffect } from "react";

export default function HotspotDetailPage() {
  const { clusterId } = useParams();
  const { data: h, loading, error, refetch } = useHotspotDetail(clusterId);
  const [impactData, setImpactData] = useState(null);
  useEffect(() => {
  if (!clusterId) return;
  fetch(`${import.meta.env.VITE_API_BASE_URL}/impact-scores`)
    .then((r) => r.json())
    .then((d) => {
      const item = d?.items?.find((x) => String(x.cluster_id) === String(clusterId));
      setImpactData(item || null);
    })
    .catch(() => {});
  }, [clusterId]);

  return (
    <>
      <Link to="/hotspots" className="inline-flex items-center gap-1.5 text-sm text-paper-500 hover:text-paper-100 mb-4">
        <ArrowLeft className="w-3.5 h-3.5" /> Back to hotspots
      </Link>

      {loading && <LoadingState label="Loading hotspot…" />}
      {!loading && error && <ErrorState error={error} onRetry={refetch} />}

      {!loading && !error && h && (
        <>
          <PageHeader
            title={fmtOrDash(h.top_junction)}
            subtitle={`${fmtOrDash(h.police_station)} · ${fmtOrDash(h.district)} · cluster #${h.cluster_id}`}
            action={<RiskTierBadge tier={h.risk_tier} />}
          />

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Panel title="Violation profile">
              <dl className="text-sm space-y-2">
                <Row label="Violations" value={fmtNumber(h.violations)} status="REAL_DATA" />
                <Row label="Junctions merged" value={fmtNumber(h.n_junctions)} status="REAL_DATA" />
                <Row label="At junction" value={fmtPercent(h.pct_at_junction)} status="REAL_DATA" />
                <Row label="At peak hour" value={fmtPercent(h.pct_peak_hour)} status="REAL_DATA" />
                <Row label="Top vehicle type" value={fmtOrDash(h.top_vehicle)} status="REAL_DATA" />
                <Row label="Peak hour" value={h.peak_hour != null ? `${h.peak_hour}:00` : "—"} status="REAL_DATA" />
                <Row label="Risk score" value={fmtNumber(h.risk_score, { maximumFractionDigits: 1 })} status="REAL_DATA" />
                {(h.ci_low != null || h.ci_high != null) && (
                  <Row label="Risk 90% CI" value={`[${fmtNumber(h.ci_low)}, ${fmtNumber(h.ci_high)}]`} />
                )}
                {h.multi_jurisdiction != null && (
                  <Row label="Multi-jurisdiction" value={h.multi_jurisdiction ? "Yes" : "No"} />
                )}
              </dl>
              {h.station_breakdown && Object.keys(h.station_breakdown).length > 0 && (
                <div className="mt-4 pt-3 border-t border-ink-700">
                  <div className="text-xs font-data uppercase tracking-wide text-paper-500 mb-2">
                    Police station breakdown
                  </div>
                  {Object.entries(h.station_breakdown).map(([station, pct]) => (
                    <div key={station} className="flex justify-between text-sm py-0.5">
                      <span className="text-paper-300">{station}</span>
                      <span className="font-data">{fmtPercent(pct)}</span>
                    </div>
                  ))}
                </div>
              )}
            </Panel>

            <Panel title="Traffic congestion">
              <dl className="text-sm space-y-2">
                <Row
                  label="Congestion index"
                  value={fmtNumber(h.congestion_index, { maximumFractionDigits: 2 })}
                  status={h.traffic_validation_status}
                />
                <Row label="Avg speed" value={h.avg_speed_kmh != null ? `${fmtNumber(h.avg_speed_kmh, { maximumFractionDigits: 1 })} km/h` : "—"} />
                <Row label="Delay" value={h.delay_minutes != null ? `${fmtNumber(h.delay_minutes, { maximumFractionDigits: 1 })} min` : "—"} />
              </dl>
              {!h.congestion_index && (
                <p className="text-xs text-paper-500 mt-3">
                  No traffic probe data for this cluster. Set GOOGLE_MAPS_API_KEY and re-run the pipeline to enable this.
                </p>
              )}
            </Panel>

            <Panel title="Road capacity">
              <dl className="text-sm space-y-2">
                <Row label="Road class" value={fmtOrDash(h.road_class)} />
                <Row label="Lanes" value={fmtNumber(h.lane_count)} />
                <Row label="Width" value={h.road_width_m != null ? `${fmtNumber(h.road_width_m, { maximumFractionDigits: 1 })} m` : "—"} />
                <Row
                  label="Capacity loss"
                  value={fmtPercent(h.capacity_loss_pct)}
                  status={h.geometry_validation_status}
                />
                <Row label="ERCI index" value={fmtNumber(h.erci_index, { maximumFractionDigits: 1 })} />
                <Row label="Geometry source" value={fmtOrDash(h.geometry_source)} />
                <Row label="Confidence" value={fmtOrDash(h.confidence_level)} />
              </dl>
            </Panel>
          </div>

          {impactData && (
  <>
    {/* Impact Score Breakdown */}
    <Panel title="Impact Score — Why this hotspot matters" className="mt-4">
      <div className="flex items-center gap-4 mb-4">
        <div className="text-5xl font-bold text-amber-400 font-mono">
          {impactData.impact_score?.toFixed(0)}
        </div>
        <div>
          <div className={`text-sm font-bold px-3 py-1 rounded-full inline-block ${
            impactData.priority === "CRITICAL" ? "bg-red-900/30 text-red-400" :
            impactData.priority === "HIGH" ? "bg-orange-900/30 text-orange-400" :
            impactData.priority === "MEDIUM" ? "bg-yellow-900/30 text-yellow-400" :
            "bg-green-900/30 text-green-400"
          }`}>
            {impactData.priority}
          </div>
          <div className="text-xs text-gray-500 mt-1">
            Expected traffic improvement if enforced
          </div>
        </div>
      </div>
      <div className="space-y-2">
        {[
          { label: "Violation Volume", key: "violation_volume", weight: "30%" },
          { label: "Congestion Severity", key: "congestion_severity", weight: "25%" },
          { label: "Capacity Loss", key: "capacity_loss", weight: "20%" },
          { label: "Peak Hour Density", key: "peak_hour_density", weight: "10%" },
          { label: "Road Importance", key: "road_importance", weight: "10%" },
          { label: "Vehicle Severity", key: "vehicle_severity", weight: "5%" },
        ].map(({ label, key, weight }) => {
          const val = impactData.factors?.[key] || 0;
          return (
            <div key={key}>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-gray-400">{label}</span>
                <div className="flex gap-3">
                  <span className="text-gray-600">{weight}</span>
                  <span className="text-amber-400 font-mono">{val.toFixed(0)}/100</span>
                </div>
              </div>
              <div className="h-1.5 bg-gray-800 rounded-full overflow-hidden">
                <div
                  className="h-full bg-amber-400 rounded-full transition-all"
                  style={{ width: `${val}%` }}/>
              </div>
            </div>
          );
        })}
      </div>
    </Panel>
  </>
)}

          {h.lat != null && h.lon != null && (
            <Panel title="Location" className="mt-4">
              <div className="text-sm font-data text-paper-300">
                {fmtNumber(h.lat, { maximumFractionDigits: 5 })}, {fmtNumber(h.lon, { maximumFractionDigits: 5 })}
              </div>
              <a
                className="text-xs text-amber-400 hover:underline mt-1 inline-block"
                href={`https://www.openstreetmap.org/?mlat=${h.lat}&mlon=${h.lon}#map=17/${h.lat}/${h.lon}`}
                target="_blank"
                rel="noreferrer"
              >
                Open in OpenStreetMap →
              </a>
            </Panel>
          )}
        </>
      )}
    </>
  );
}

function Row({ label, value, status }) {
  return (
    <div className="flex items-center justify-between gap-4">
      <dt className="text-paper-500">{label}</dt>
      <dd className="font-data text-paper-100 text-right flex items-center gap-2">
        {value}
        {status && <EvidenceChip status={status} />}
      </dd>
    </div>
  );
}
