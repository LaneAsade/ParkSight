import { useState } from "react";
import { useEvidence, useEvidenceSummary } from "../hooks/useEvidence";
import { PageHeader, Panel } from "../components/Panel";
import EvidenceChip from "../components/EvidenceChip";
import { LoadingState, ErrorState, EmptyState } from "../components/StatusStates";

const STATUS_FILTERS = ["ALL", "REAL_DATA", "MODELED", "PARTIAL", "SPEC_ONLY"];

export default function EvidencePage() {
  const [status, setStatus] = useState("ALL");
  const summary = useEvidenceSummary();
  const filters = status === "ALL" ? {} : { status };
  const evidence = useEvidence(filters);
  const items = evidence.data?.items || [];

  return (
    <>
      <PageHeader
        title="Evidence ledger"
        subtitle="Every claim this console makes, in one place, tagged with how it was produced. Nothing here is upgraded from its source stage's own label."
        action={
          <div className="flex gap-1.5">
            {STATUS_FILTERS.map((s) => (
              <button
                key={s}
                onClick={() => setStatus(s)}
                className={`text-xs font-data px-3 py-1 rounded-full border transition-colors ${
                  status === s
                    ? "border-amber-400 text-amber-400 bg-amber-400/10"
                    : "border-ink-700 text-paper-500 hover:text-paper-100 hover:border-ink-500"
                }`}
              >
                {s}
              </button>
            ))}
          </div>
        }
      />

      {!summary.loading && !summary.error && summary.data && (
        <div className="flex gap-3 mb-6 flex-wrap">
          {Object.entries(summary.data.counts || {}).map(([s, count]) => (
            <div key={s} className="flex items-center gap-2 flare-card rounded-xl px-3 py-2">
              <EvidenceChip status={s} />
              <span className="font-data text-sm text-paper-100">{count}</span>
            </div>
          ))}
        </div>
      )}

      {evidence.loading && <LoadingState label="Loading evidence ledger…" />}
      {!evidence.loading && evidence.error && <ErrorState error={evidence.error} onRetry={evidence.refetch} />}
      {!evidence.loading && !evidence.error && evidence.empty && (
        <EmptyState title="No evidence records match this filter" />
      )}

      {!evidence.loading && !evidence.error && items.length > 0 && (
        <Panel title={`${evidence.data.total} claim${evidence.data.total === 1 ? "" : "s"}`}>
          <div className="overflow-x-auto -mx-4">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs font-data uppercase tracking-wide text-paper-500 border-b border-ink-700">
                  <th className="px-4 py-2">Claim</th>
                  <th className="px-4 py-2">Value</th>
                  <th className="px-4 py-2">Status</th>
                  <th className="px-4 py-2">Source</th>
                  <th className="px-4 py-2">Confidence</th>
                </tr>
              </thead>
              <tbody>
                {items.map((e, i) => (
                  <tr key={i} className="border-b border-ink-800 align-top">
                    <td className="px-4 py-2.5 text-paper-100 max-w-md">{e.claim}</td>
                    <td className="px-4 py-2.5 font-data text-paper-100 whitespace-nowrap">{e.value ?? "—"}</td>
                    <td className="px-4 py-2.5">
                      <EvidenceChip status={e.status} />
                    </td>
                    <td className="px-4 py-2.5 text-paper-500 font-data text-xs">{e.source ?? "—"}</td>
                    <td className="px-4 py-2.5 text-paper-500 text-xs">{e.confidence ?? "—"}</td>
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
