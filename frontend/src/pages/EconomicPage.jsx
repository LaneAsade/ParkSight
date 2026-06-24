import { useEconomicAssumptions as useEconomic } from "../hooks/useEconomic";
import { PageHeader, Panel } from "../components/Panel";
import { LoadingState, ErrorState } from "../components/StatusStates";
import EvidenceChip from "../components/EvidenceChip";

function formatINR(v) {
  if (v == null) return "—";
  if (v >= 10000000) return `₹${(v / 10000000).toFixed(1)}Cr`;
  if (v >= 100000) return `₹${(v / 100000).toFixed(1)}L`;
  return `₹${Math.round(v).toLocaleString("en-IN")}`;
}

export default function EconomicPage() {
  const { data, loading, error, refetch } = useEconomic();

  return (
    <>
      <PageHeader
        title="Economic Impact"
        subtitle="Modeled fuel and time costs associated with illegal-parking-induced capacity loss. IRC:106-2010 engineering estimates — not measured causal effects."
      />

      {loading && <LoadingState label="Loading economic model…" />}
      {!loading && error && <ErrorState error={error} onRetry={refetch} />}

      {!loading && !error && data && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {[
              { label: "Fuel cost / year", value: formatINR(data.total_fuel_cost_inr_per_year) },
              { label: "Time cost / year", value: formatINR(data.total_time_cost_inr_per_year) },
              { label: "Total modeled impact", value: formatINR(data.total_modeled_impact_inr_per_year) },
              { label: "CO₂ / year", value: data.total_co2_kg_per_year ? `${Math.round(data.total_co2_kg_per_year / 1000)} t` : "—" },
            ].map(({ label, value }) => (
              <Panel key={label} title={label}>
                <div className="text-2xl font-display font-bold text-amber-400">{value}</div>
                <EvidenceChip status="MODELED" className="mt-2" />
              </Panel>
            ))}
          </div>

          {data.sensitivity_scenarios_inr_per_year && (
            <Panel title="Sensitivity scenarios">
              <div className="grid grid-cols-3 gap-3">
                {Object.entries(data.sensitivity_scenarios_inr_per_year).map(([k, v]) => (
                  <div key={k} className="text-center">
                    <div className="text-xs text-paper-500 mb-1">{k}</div>
                    <div className="text-lg font-data font-semibold text-paper-100">{formatINR(v)}</div>
                  </div>
                ))}
              </div>
            </Panel>
          )}

          {data.causal_caveat && (
            <div className="text-xs text-paper-500 bg-ink-900 border border-ink-700 rounded-xl px-4 py-3">
              ⚠ {data.causal_caveat}
            </div>
          )}
        </div>
      )}
    </>
  );
}