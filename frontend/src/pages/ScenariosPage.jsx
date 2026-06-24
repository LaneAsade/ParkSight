// frontend/src/pages/ScenariosPage.jsx
import { useState } from "react";
import { PageHeader, Panel } from "../components/Panel";
import { fmtNumber, fmtPercent } from "../utils/format";

const SCENARIO_TYPES = [
  { id: "patrol", label: "Add Patrol Teams", icon: "🚔" },
  { id: "remove_patrol", label: "Remove Patrol Teams", icon: "🚫" },
  { id: "no_parking", label: "Temp No-Parking Zone", icon: "🚷" },
  { id: "concert", label: "Concert Event", icon: "🎵" },
  { id: "sports", label: "Sports Event", icon: "🏟️" },
  { id: "festival", label: "Festival", icon: "🎉" },
];

function DeltaBadge({ baseline, scenario, fmt }) {
  if (baseline == null || scenario == null) return <span className="text-gray-500">—</span>;
  const delta = scenario - baseline;
  const positive = delta > 0;
  return (
    <span className={positive ? "text-green-400" : "text-red-400"}>
      {positive ? "+" : ""}{fmt ? fmt(delta) : delta.toFixed(1)}
    </span>
  );
}

export default function ScenariosPage() {
  const [scenarioType, setScenarioType] = useState("patrol");
  const [additionalTeams, setAdditionalTeams] = useState(2);
  const [violationReduction, setViolationReduction] = useState(30);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function runScenario() {
    setLoading(true);
    setError(null);
    try {
      const teams = scenarioType === "remove_patrol" ? -Math.abs(additionalTeams) : additionalTeams;
      const res = await fetch(
        `${import.meta.env.VITE_API_BASE_URL}/scenarios/simulate`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            additional_patrol_teams: teams,
            risk_tier_thresholds: null,
            economic_overrides: null,
            assumed_violation_reduction_pct: violationReduction,
          }),
        }
      );
      const data = await res.json();
      setResult(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  const baselineCoverage = result?.baseline?.coverage_pct?.value;
  const scenarioCoverage = result?.scenario?.coverage_pct?.value;
  const baselineImpact = result?.baseline?.annual_modeled_impact_inr?.value;
  const scenarioImpact = result?.scenario?.annual_modeled_impact_inr?.value;
  const baselineCritical = result?.baseline?.critical_covered?.value;
  const scenarioCritical = result?.scenario?.critical_covered?.value;

  return (
    <div className="p-6 space-y-4 max-w-5xl mx-auto">
      <PageHeader
        title="Scenario Simulator — Digital Twin"
        subtitle="Test enforcement decisions before deployment. All projections are MODELED — not measured outcomes."
      />

      {/* Scenario type picker */}
      <Panel title="Select Scenario">
        <div className="grid grid-cols-3 md:grid-cols-6 gap-2">
          {SCENARIO_TYPES.map((s) => (
            <button
              key={s.id}
              onClick={() => setScenarioType(s.id)}
              className={`flex flex-col items-center gap-1.5 px-3 py-3 rounded-xl border text-xs transition-all ${
                scenarioType === s.id
                  ? "bg-amber-400/15 border-amber-400/60 text-amber-400"
                  : "bg-gray-800/50 border-gray-700 text-gray-400 hover:border-gray-500"
              }`}
            >
              <span className="text-xl">{s.icon}</span>
              <span className="font-medium text-center leading-tight">{s.label}</span>
            </button>
          ))}
        </div>
      </Panel>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Panel title="Controls">
          <div className="space-y-5">
            <div>
              <label className="block text-xs font-mono uppercase tracking-wide text-gray-500 mb-2">
                {scenarioType === "remove_patrol" ? "Teams to remove" : "Additional patrol teams"}: <span className="text-amber-400 font-bold">{additionalTeams}</span>
              </label>
              <input
                type="range" min={0} max={20} value={additionalTeams}
                onChange={(e) => setAdditionalTeams(+e.target.value)}
                className="w-full accent-amber-400"
              />
              <div className="flex justify-between text-xs text-gray-600 mt-1">
                <span>0</span><span>20</span>
              </div>
            </div>

            <div>
              <label className="block text-xs font-mono uppercase tracking-wide text-gray-500 mb-2">
                Assumed violation reduction: <span className="text-amber-400 font-bold">{violationReduction}%</span>
              </label>
              <input
                type="range" min={0} max={100} value={violationReduction}
                onChange={(e) => setViolationReduction(+e.target.value)}
                className="w-full accent-amber-400"
              />
            </div>

            <button
              onClick={runScenario}
              disabled={loading}
              className="w-full py-3 rounded-xl bg-amber-400 text-gray-950 font-bold text-sm hover:bg-amber-300 disabled:opacity-50 transition-colors"
            >
              {loading ? "Simulating…" : "▶ Run Simulation"}
            </button>

            {error && (
              <div className="text-sm text-red-400 bg-red-900/20 rounded-lg px-3 py-2">
                Error: {error}
              </div>
            )}
          </div>
        </Panel>

        {result && (
          <Panel title="Simulation Results">
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3 text-center mb-2">
                <div className="bg-gray-800/60 rounded-xl p-3">
                  <div className="text-xs text-gray-500 font-mono mb-1">BASELINE</div>
                  <div className="text-2xl font-bold text-gray-300">{fmtPercent(baselineCoverage)}</div>
                  <div className="text-xs text-gray-500">coverage</div>
                </div>
                <div className="bg-amber-400/10 border border-amber-400/30 rounded-xl p-3">
                  <div className="text-xs text-amber-400 font-mono mb-1">SCENARIO</div>
                  <div className="text-2xl font-bold text-amber-400">{fmtPercent(scenarioCoverage)}</div>
                  <div className="text-xs text-amber-500">coverage</div>
                </div>
              </div>

              {[
                {
                  label: "Patrol Coverage",
                  baseline: fmtPercent(baselineCoverage),
                  scenario: fmtPercent(scenarioCoverage),
                  delta: scenarioCoverage != null && baselineCoverage != null
                    ? `${((scenarioCoverage - baselineCoverage) * 100).toFixed(1)}pp`
                    : null,
                  up: scenarioCoverage > baselineCoverage,
                },
                {
                  label: "Critical Zones Covered",
                  baseline: fmtNumber(baselineCritical),
                  scenario: fmtNumber(scenarioCritical),
                  delta: scenarioCritical != null && baselineCritical != null
                    ? `+${scenarioCritical - baselineCritical}`
                    : null,
                  up: scenarioCritical > baselineCritical,
                },
                {
                  label: "Modelled Annual Impact",
                  baseline: baselineImpact ? `₹${fmtNumber(baselineImpact)}` : "—",
                  scenario: scenarioImpact ? `₹${fmtNumber(scenarioImpact)}` : "—",
                  delta: null,
                  up: null,
                },
              ].map(({ label, baseline, scenario, delta, up }) => (
                <div key={label} className="flex items-center justify-between text-sm border-b border-gray-800 pb-3">
                  <span className="text-gray-400">{label}</span>
                  <div className="flex items-center gap-3 font-mono text-right">
                    <span className="text-gray-500 text-xs">{baseline}</span>
                    <span className="text-gray-600">→</span>
                    <span className="text-gray-100 font-semibold">{scenario}</span>
                    {delta && (
                      <span className={`text-xs font-bold ${up ? "text-green-400" : "text-red-400"}`}>
                        {delta}
                      </span>
                    )}
                  </div>
                </div>
              ))}

              <div className="text-xs text-gray-600 pt-1 border-t border-gray-800">
                ⚠ All outputs are MODELLED projections. Actual outcomes may differ.
              </div>
            </div>
          </Panel>
        )}
      </div>
    </div>
  );
}