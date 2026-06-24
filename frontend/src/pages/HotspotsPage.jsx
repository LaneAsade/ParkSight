import { useState } from "react";
import { Link } from "react-router-dom";
import { useHotspots } from "../hooks/useHotspots";
import { PageHeader, Panel } from "../components/Panel";
import RiskTierBadge from "../components/RiskTierBadge";
import EvidenceChip from "../components/EvidenceChip";
import { LoadingState, ErrorState, EmptyState } from "../components/StatusStates";
import { fmtNumber, fmtPercent, fmtOrDash } from "../utils/format";

const TIER_FILTERS = ["ALL", "CRITICAL", "HIGH", "MEDIUM", "LOW"];

export default function HotspotsPage() {
  const [tier, setTier] = useState("ALL");
  const filters = tier === "ALL" ? {} : { risk_tier: tier };
  const { data, loading, error, empty, refetch } = useHotspots(filters);
  const items = data?.items || [];

  return (
    <>
      <PageHeader
        title="Hotspots"
        subtitle="DBSCAN-detected junction clusters, ranked by composite risk score. Click a row for the full evidence breakdown."
        action={
          <div className="flex gap-1.5">
            {TIER_FILTERS.map((t) => (
              <button
                key={t}
                onClick={() => setTier(t)}
                className={`text-xs font-data px-3 py-1 rounded-full border transition-colors ${
                  tier === t
                    ? "border-amber-400 text-amber-400 bg-amber-400/10"
                    : "border-ink-700 text-paper-500 hover:text-paper-100 hover:border-ink-500"
                }`}
              >
                {t}
              </button>
            ))}
          </div>
        }
      />

      {loading && <LoadingState label="Loading hotspots…" />}
      {!loading && error && <ErrorState error={error} onRetry={refetch} />}
      {!loading && !error && empty && (
        <EmptyState title="No hotspots match this filter" hint="Try a different risk tier, or check that the pipeline run produced hotspot_clusters.csv." />
      )}

      {!loading && !error && items.length > 0 && (
        <Panel title={`${data.total} hotspot${data.total === 1 ? "" : "s"}`}>
          <div className="overflow-x-auto -mx-4">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs font-data uppercase tracking-wide text-paper-500 border-b border-ink-700">
                  <th className="px-4 py-2">Junction</th>
                  <th className="px-4 py-2">District</th>
                  <th className="px-4 py-2 text-right">Violations</th>
                  <th className="px-4 py-2 text-right">At junction</th>
                  <th className="px-4 py-2 text-right">Risk score</th>
                  <th className="px-4 py-2">Tier</th>
                  <th className="px-4 py-2">Congestion</th>
                </tr>
              </thead>
              <tbody>
                {items.map((h) => (
                  <tr
                    key={h.cluster_id}
                    className="border-b border-ink-800 hover:bg-amber-400/[0.04] transition-colors"
                  >
                    <td className="px-4 py-2.5">
                      <Link to={`/hotspots/${h.cluster_id}`} className="text-paper-100 hover:text-amber-400">
                        {fmtOrDash(h.top_junction)}
                      </Link>
                      <div className="text-xs text-paper-500">{fmtOrDash(h.police_station)}</div>
                    </td>
                    <td className="px-4 py-2.5 text-paper-300">{fmtOrDash(h.district)}</td>
                    <td className="px-4 py-2.5 text-right font-data">{fmtNumber(h.violations)}</td>
                    <td className="px-4 py-2.5 text-right font-data">{fmtPercent(h.pct_at_junction)}</td>
                    <td className="px-4 py-2.5 text-right font-data">{fmtNumber(h.risk_score, { maximumFractionDigits: 1 })}</td>
                    <td className="px-4 py-2.5">
                      <RiskTierBadge tier={h.risk_tier} />
                    </td>
                    <td className="px-4 py-2.5">
                      {h.congestion_index != null ? (
                        <span className="flex items-center gap-2 font-data">
                          {fmtNumber(h.congestion_index, { maximumFractionDigits: 2 })}
                          <EvidenceChip status={h.traffic_validation_status} />
                        </span>
                      ) : (
                        <EvidenceChip status={h.traffic_validation_status || "SPEC_ONLY"} />
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
      )}
    </>
  );
}
