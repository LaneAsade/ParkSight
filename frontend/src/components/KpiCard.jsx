import EvidenceChip from "./EvidenceChip";

/**
 * KpiCard — a single headline metric. `status` is optional; when provided
 * it renders an EvidenceChip so every number's provenance is visible right
 * next to it, not buried in a tooltip.
 */
export default function KpiCard({ label, value, status, hint }) {
  return (
    <div className="flare-card rounded-xl px-4 py-3.5">
      <div className="flex items-center justify-between gap-2">
        <div className="text-xs font-data uppercase tracking-wide text-paper-500">{label}</div>
        {status && <EvidenceChip status={status} />}
      </div>
      <div className="mt-1.5 font-display text-2xl font-bold text-paper-100">{value}</div>
      {hint && <div className="mt-1 text-xs text-paper-500">{hint}</div>}
    </div>
  );
}
