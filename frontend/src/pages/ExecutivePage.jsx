// frontend/src/pages/ExecutivePage.jsx
import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { LoadingState, ErrorState } from "../components/StatusStates";
import { fmtNumber, fmtPercent } from "../utils/format";

const PRIORITY_COLORS = {
  CRITICAL: "text-red-400 bg-red-900/20 border-red-800/40",
  HIGH: "text-orange-400 bg-orange-900/20 border-orange-800/40",
  MEDIUM: "text-yellow-400 bg-yellow-900/20 border-yellow-800/40",
  LOW: "text-green-400 bg-green-900/20 border-green-800/40",
};

function SectionTitle({ children }) {
  return (
    <div className="text-xs font-mono uppercase tracking-widest text-gray-500 mb-3 border-b border-gray-800 pb-1.5">
      {children}
    </div>
  );
}

function ImpactRow({ rank, item }) {
  const cls = PRIORITY_COLORS[item.priority] || PRIORITY_COLORS.LOW;
  return (
    <div className="flex items-center gap-3 py-2.5 border-b border-gray-800/60 last:border-0">
      <span className="text-lg font-bold text-gray-700 w-6 shrink-0">{rank}</span>
      <div className="flex-1 min-w-0">
        <div className="text-sm font-semibold text-gray-100 truncate">{item.top_junction || `Cluster ${item.cluster_id}`}</div>
        <div className="text-xs text-gray-500">{item.district}</div>
      </div>
      <div className="text-right shrink-0">
        <div className={`text-xs px-2 py-0.5 rounded border font-mono ${cls}`}>
          {item.priority || item.priority_tier}
        </div>
        <div className="text-xs text-amber-400 font-mono mt-0.5">
          Score: {item.impact_score?.toFixed(0)}
        </div>
      </div>
    </div>
  );
}

function CapLossRow({ rank, item }) {
  const pct = item.capacity_loss_pct || 0;
  return (
    <div className="py-2.5 border-b border-gray-800/60 last:border-0">
      <div className="flex items-center justify-between mb-1">
        <div className="flex items-center gap-2">
          <span className="text-sm font-bold text-gray-600">#{rank}</span>
          <span className="text-sm text-gray-200 truncate">{item.top_junction || `Cluster ${item.cluster_id}`}</span>
        </div>
        <span className="text-sm font-bold text-red-400 font-mono">{fmtPercent(pct)}</span>
      </div>
      <div className="h-1.5 bg-gray-800 rounded-full overflow-hidden">
        <div
          className="h-full bg-red-500 rounded-full"
          style={{ width: `${Math.min(pct * 100, 100)}%` }}
        />
      </div>
    </div>
  );
}

function OpportunityRow({ rank, item }) {
  return (
    <div className="flex items-center gap-3 py-2.5 border-b border-gray-800/60 last:border-0">
      <span className="text-lg font-bold text-gray-700 w-6 shrink-0">{rank}</span>
      <div className="flex-1 min-w-0">
        <div className="text-sm font-semibold text-gray-100 truncate">{item.top_junction}</div>
        <div className="text-xs text-gray-500">{item.recommended_action}</div>
      </div>
      <div className="text-right shrink-0">
        <div className="text-sm font-bold text-green-400 font-mono">
          +{item.expected_recovery_pct}%
        </div>
        <div className="text-xs text-gray-500">recovery</div>
      </div>
    </div>
  );
}

export default function ExecutivePage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch(`${import.meta.env.VITE_API_BASE_URL}/executive/summary`)
      .then((r) => r.json())
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingState label="Loading executive summary…" />;
  if (error) return <ErrorState error={error} />;
  if (!data) return null;

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-100">Executive Intelligence</h1>
          <p className="text-sm text-gray-500 mt-0.5">Decision-ready summary for senior traffic operations leadership</p>
        </div>
        <div className="text-right text-xs font-mono text-gray-500">
          {new Date().toLocaleDateString("en-IN", { dateStyle: "long" })}
        </div>
      </div>

      {/* Top KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { label: "Critical Zones", value: data.critical_zones, color: "text-red-400" },
          { label: "Immediate Actions", value: data.immediate_actions_required, color: "text-orange-400" },
          { label: "Avg Expected Recovery", value: `${data.avg_expected_recovery_pct}%`, color: "text-green-400" },
          {
            label: "Annual Economic Impact",
            value: data.economic_summary?.total_modeled_impact_inr_per_year
              ? `₹${fmtNumber(data.economic_summary.total_modeled_impact_inr_per_year)}`
              : "—",
            color: "text-amber-400",
          },
        ].map(({ label, value, color }) => (
          <div key={label} className="bg-gray-900 border border-gray-800 rounded-xl px-4 py-3">
            <div className="text-xs font-mono uppercase tracking-widest text-gray-500 mb-1">{label}</div>
            <div className={`text-2xl font-bold ${color}`}>{value}</div>
          </div>
        ))}
      </div>

      {/* Recommended Actions Banner */}
      {data.recommended_actions?.length > 0 && (
        <div className="bg-amber-400/10 border border-amber-400/30 rounded-xl px-4 py-3">
          <div className="text-xs font-mono uppercase tracking-widest text-amber-400 mb-2">
            ⚡ Recommended Immediate Actions
          </div>
          <div className="space-y-1">
            {data.recommended_actions.map((action, i) => (
              <div key={i} className="text-sm text-gray-200 flex gap-2">
                <span className="text-amber-400 font-bold">{i + 1}.</span>
                {action}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Main Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Top Congestion Drivers */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
          <SectionTitle>Top Congestion Drivers</SectionTitle>
          {data.top5_congestion_drivers?.map((item, i) => (
            <ImpactRow key={item.cluster_id} rank={i + 1} item={item} />
          ))}
          <Link to="/hotspots" className="text-xs text-amber-400 hover:underline mt-2 inline-block">
            View all hotspots →
          </Link>
        </div>

        {/* Highest Capacity Loss */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
          <SectionTitle>Highest Capacity Loss Corridors</SectionTitle>
          {data.highest_capacity_loss_corridors?.map((item, i) => (
            <CapLossRow key={item.cluster_id} rank={i + 1} item={item} />
          ))}
          <Link to="/congestion" className="text-xs text-amber-400 hover:underline mt-2 inline-block">
            View congestion analysis →
          </Link>
        </div>

        {/* Enforcement Opportunities */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
          <SectionTitle>Enforcement Opportunities</SectionTitle>
          {data.top5_enforcement_opportunities?.map((item, i) => (
            <OpportunityRow key={item.cluster_id} rank={i + 1} item={item} />
          ))}
          <Link to="/patrol" className="text-xs text-amber-400 hover:underline mt-2 inline-block">
            View patrol plan →
          </Link>
        </div>
      </div>

      <div className="text-xs text-gray-600 text-center">
        ⚠ All projections are MODELED. Validate with field data before operational deployment.
      </div>
    </div>
  );
}