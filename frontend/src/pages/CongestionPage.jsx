import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  ScatterChart, Scatter, ZAxis,
} from "recharts";
import { useCongestionSummary, useCongestionByDistrict, useCongestionRelationship } from "../hooks/useCongestion";
import { PageHeader, Panel } from "../components/Panel";
import KpiCard from "../components/KpiCard";
import { LoadingState, ErrorState, EmptyState } from "../components/StatusStates";
import { fmtNumber } from "../utils/format";

const TIER_COLOR = { CRITICAL: "#E5484D", HIGH: "#F2A33C", MEDIUM: "#E9C46A", LOW: "#5FA8D3" };

export default function CongestionPage() {
  const summary = useCongestionSummary();
  const byDistrict = useCongestionByDistrict();
  const relationship = useCongestionRelationship();

  return (
    <>
      <PageHeader
        title="Congestion"
        subtitle="Real-time traffic probes against detected hotspots. Probes that failed or were never attempted are shown as unavailable, never estimated."
      />

      {summary.loading && <LoadingState label="Loading congestion summary…" />}
      {!summary.loading && summary.error && <ErrorState error={summary.error} onRetry={summary.refetch} />}
      {!summary.loading && !summary.error && summary.data && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
          <KpiCard label="Hotspots probed" value={fmtNumber(summary.data.total_hotspots)} />
          <KpiCard label="Real data" value={fmtNumber(summary.data.real_data_count)} status="REAL_DATA" />
          <KpiCard label="Partial" value={fmtNumber(summary.data.partial_count)} status="PARTIAL" />
          <KpiCard label="Unavailable" value={fmtNumber(summary.data.spec_only_count)} status="SPEC_ONLY" />
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Panel title="Mean delay by district">
          {byDistrict.loading && <LoadingState />}
          {!byDistrict.loading && byDistrict.error && <ErrorState error={byDistrict.error} onRetry={byDistrict.refetch} />}
          {!byDistrict.loading && !byDistrict.error && byDistrict.empty && <EmptyState title="No district-level congestion data" />}
          {!byDistrict.loading && !byDistrict.error && byDistrict.data?.length > 0 && (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={byDistrict.data} margin={{ left: -20 }}>
                <CartesianGrid stroke="#1F2730" vertical={false} />
                <XAxis dataKey="district" tick={{ fill: "#8C98A4", fontSize: 11 }} interval={0} angle={-20} textAnchor="end" height={60} />
                <YAxis tick={{ fill: "#8C98A4", fontSize: 11 }} label={{ value: "min", position: "insideLeft", fill: "#8C98A4", fontSize: 11 }} />
                <Tooltip
                  contentStyle={{ background: "#161D26", border: "1px solid #2B3540", fontSize: 12 }}
                  labelStyle={{ color: "#E8ECEF" }}
                />
                <Bar dataKey="mean_delay_minutes" fill="#F2A33C" radius={[3, 3, 0, 0]} name="Mean delay (min)" />
              </BarChart>
            </ResponsiveContainer>
          )}
        </Panel>

        <Panel title="Violations vs. congestion index">
          {relationship.loading && <LoadingState />}
          {!relationship.loading && relationship.error && <ErrorState error={relationship.error} onRetry={relationship.refetch} />}
          {!relationship.loading && !relationship.error && relationship.data?.points?.length > 0 && (
            <>
              <ResponsiveContainer width="100%" height={230}>
                <ScatterChart margin={{ left: -20, top: 10 }}>
                  <CartesianGrid stroke="#1F2730" />
                  <XAxis
                    type="number"
                    dataKey="violations"
                    name="Violations"
                    tick={{ fill: "#8C98A4", fontSize: 11 }}
                    label={{ value: "Violations", position: "insideBottom", offset: -5, fill: "#8C98A4", fontSize: 11 }}
                  />
                  <YAxis
                    type="number"
                    dataKey="congestion_index"
                    name="Congestion index"
                    tick={{ fill: "#8C98A4", fontSize: 11 }}
                  />
                  <ZAxis range={[60, 60]} />
                  <Tooltip
                    cursor={{ strokeDasharray: "3 3" }}
                    contentStyle={{ background: "#161D26", border: "1px solid #2B3540", fontSize: 12 }}
                  />
                  <Scatter
                    data={relationship.data.points.filter((p) => p.congestion_index != null)}
                    fill="#5FA8D3"
                    shape={(props) => {
                      const { cx, cy, payload } = props;
                      return <circle cx={cx} cy={cy} r={5} fill={TIER_COLOR[payload.risk_tier] || "#8C98A4"} fillOpacity={0.85} />;
                    }}
                  />
                </ScatterChart>
              </ResponsiveContainer>
              <p className="text-xs text-paper-500 mt-2">{relationship.data.observational_caveat}</p>
            </>
          )}
          {!relationship.loading && !relationship.error && (!relationship.data?.points || relationship.data.points.length === 0) && (
            <EmptyState title="No traffic-validated hotspots yet" hint="Provide GOOGLE_MAPS_API_KEY and re-run the pipeline." />
          )}
        </Panel>
      </div>
    </>
  );
}
