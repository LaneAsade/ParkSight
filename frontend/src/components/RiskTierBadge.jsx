const TIER_STYLES = {
  CRITICAL: "bg-tier-critical/15 text-tier-critical border-tier-critical/40",
  HIGH: "bg-tier-high/15 text-tier-high border-tier-high/40",
  MEDIUM: "bg-tier-medium/15 text-tier-medium border-tier-medium/40",
  LOW: "bg-tier-low/15 text-tier-low border-tier-low/40",
};

export default function RiskTierBadge({ tier }) {
  if (!tier) return <span className="text-paper-500 font-data text-xs">—</span>;
  const cls = TIER_STYLES[tier] || "bg-paper-500/15 text-paper-500 border-paper-500/40";
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-data font-semibold uppercase tracking-wide ${cls}`}
    >
      {tier}
    </span>
  );
}
