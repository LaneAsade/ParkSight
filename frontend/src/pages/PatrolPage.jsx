import { useState } from "react";
import { usePatrol } from "../hooks/usePatrol";
import { PageHeader, Panel } from "../components/Panel";
import KpiCard from "../components/KpiCard";
import RiskTierBadge from "../components/RiskTierBadge";
import EvidenceChip from "../components/EvidenceChip";
import { LoadingState, ErrorState, EmptyState } from "../components/StatusStates";
import { fmtNumber, fmtPercent, fmtOrDash } from "../utils/format";

export default function PatrolPage() {
  const [teams, setTeams] = useState(10);
  const { result, loading, error } = usePatrol(teams);

  return (
    <>
      <PageHeader
        title="Patrol optimization"
        subtitle="MILP-based assignment of patrol teams to hotspots by shift, maximizing coverage of critical-tier locations first."
        action={
          <div className="flex items-center gap-3">
            <label htmlFor="teams" className="text-xs font-data text-paper-500">
              Teams
            </label>
            <input
              id="teams"
              type="range"
              min={1}
              max={50}
              value={teams}
              onChange={(e) => setTeams(Number(e.target.value))}
              className="w-40 accent-amber-400"
            />
            <span className="font-data text-sm text-paper-100 w-6 text-right">{teams}</span>
          </div>
        }
      />

      {loading && <LoadingState label="Solving assignment…" />}
      {!loading && error && <ErrorState error={error} />}

      {!loading && !error && result && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <KpiCard
              label="Coverage"
              value={fmtPercent(result.overall_coverage_pct)}
              status={result.validation_status}
            />
            <KpiCard
              label="Critical covered"
              value={`${result.critical_covered} / ${result.critical_total}`}
              status={result.validation_status}
            />
            <KpiCard
              label="Hotspots covered"
              value={`${result.distinct_hotspots_covered} / ${result.distinct_hotspots_total}`}
            />
            <KpiCard
              label="Solver"
              value={result.solved_to_optimality ? "Optimal" : result.used_greedy_fallback ? "Greedy fallback" : "—"}
            />
          </div>

          {result.skipped_reason && (
            <div className="rounded-xl border border-evidence-partial/40 bg-evidence-partial/10 px-4 py-3 text-sm text-paper-100">
              ⚠ {result.skipped_reason}
            </div>
          )}

          <Panel title={`${result.critical_coverage_mode}`}>
            <p className="text-sm text-paper-300">{result.critical_coverage_note}</p>
          </Panel>

          {result.assignments?.length > 0 ? (
            <Panel title={`Assignments (${result.n_assignments})`}>
              <div className="overflow-x-auto -mx-4">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-xs font-data uppercase tracking-wide text-paper-500 border-b border-ink-700">
                      <th className="px-4 py-2">Hotspot</th>
                      <th className="px-4 py-2">Tier</th>
                      <th className="px-4 py-2">Shift</th>
                      <th className="px-4 py-2 text-right">Impact score</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.assignments.map((a, i) => (
                      <tr key={`${a.cluster_id}-${a.shift}-${i}`} className="border-b border-ink-800">
                        <td className="px-4 py-2.5">{fmtOrDash(a.top_junction || a.hotspot)}</td>
                        <td className="px-4 py-2.5">
                          <RiskTierBadge tier={a.risk_tier} />
                        </td>
                        <td className="px-4 py-2.5 font-data text-paper-300">{a.shift}</td>
                        <td className="px-4 py-2.5 text-right font-data">{fmtNumber(a.impact_score, { maximumFractionDigits: 1 })}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Panel>
          ) : (
            <EmptyState title="No assignments produced" hint="Increase the team count or check that hotspot data is available." />
          )}

          {result.shift_capacities && Object.keys(result.shift_capacities).length > 0 && (
            <Panel title="Shift capacities">
              <div className="flex gap-4 flex-wrap">
                {Object.entries(result.shift_capacities).map(([shift, cap]) => (
                  <div key={shift} className="text-sm">
                    <span className="font-data text-paper-100">{cap}</span>{" "}
                    <span className="text-paper-500">{shift}</span>
                  </div>
                ))}
              </div>
            </Panel>
          )}
        </div>
      )}
    </>
  );
}
