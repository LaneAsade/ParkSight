import { useForecastSummary as useForecast } from "../hooks/useForecast";
import { PageHeader, Panel } from "../components/Panel";
import { LoadingState, ErrorState } from "../components/StatusStates";
import EvidenceChip from "../components/EvidenceChip";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";

export default function ForecastPage() {
  const { data, loading, error, refetch } = useForecast();

  return (
    <>
      <PageHeader
        title="Forecast"
        subtitle="Walk-forward persistence baseline — last month's count is next month's forecast. A learned model is used only when ≥6 months of data are available."
      />

      {loading && <LoadingState label="Loading forecast…" />}
      {!loading && error && <ErrorState error={error} onRetry={refetch} />}

      {!loading && !error && data && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {[
              { label: "Months used", value: data.months_used?.length ?? "—" },
              { label: "Months excluded", value: data.excluded_months?.length ?? "—" },
              { label: "Persistence MAE", value: data.persistence_mae ?? "—" },
              { label: "Learned model", value: data.learned_model_available ? "Available" : "Not available" },
            ].map(({ label, value }) => (
              <Panel key={label} title={label}>
                <div className="text-2xl font-display font-bold text-amber-400">{value}</div>
              </Panel>
            ))}
          </div>

          <Panel title="Monthly violation trend (pipeline-wide)">
            {data.months_used?.length > 0 ? (
              <div className="h-56">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={data.months_used.map((m, i) => ({ month: m, index: i + 1 }))}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                    <XAxis dataKey="month" tick={{ fill: "#888", fontSize: 11 }} />
                    <YAxis tick={{ fill: "#888", fontSize: 11 }} />
                    <Tooltip contentStyle={{ background: "#1a1a2e", border: "1px solid #333" }} />
                    <Line type="monotone" dataKey="index" stroke="#f59e0b" dot={false} strokeWidth={2} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <p className="text-paper-500 text-sm">No monthly data available.</p>
            )}
          </Panel>

          {data.honest_caveat && (
            <div className="text-xs text-paper-500 bg-ink-900 border border-ink-700 rounded-xl px-4 py-3">
              ⚠ {data.honest_caveat}
            </div>
          )}
          <div className="flex gap-2">
            <EvidenceChip status={data.validation_status} />
          </div>
        </div>
      )}
    </>
  );
}