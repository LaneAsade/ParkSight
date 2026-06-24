// frontend/src/components/Layout.jsx
import { NavLink, Outlet } from "react-router-dom";
import {
  LayoutDashboard,
  MapPinned,
  TrafficCone,
  ShieldCheck,
  TrendingUp,
  IndianRupee,
  ListChecks,
  SlidersHorizontal,
  MessageSquareText,
  Radio,
  BarChart3,       // Executive
} from "lucide-react";
import { useSystemStatus } from "../hooks/useSystemStatus";

const NAV_ITEMS = [
  { to: "/", label: "Command Center", icon: LayoutDashboard, end: true },
  { to: "/executive", label: "Executive", icon: BarChart3 },
  { to: "/hotspots", label: "Hotspots", icon: MapPinned },
  { to: "/congestion", label: "Congestion", icon: TrafficCone },
  { to: "/patrol", label: "Patrol", icon: ShieldCheck },
  { to: "/forecast", label: "Forecast", icon: TrendingUp },
  { to: "/economic", label: "Economic", icon: IndianRupee },
  { to: "/evidence", label: "Evidence", icon: ListChecks },
  { to: "/scenarios", label: "Scenarios", icon: SlidersHorizontal },
  { to: "/copilot", label: "AI Copilot", icon: MessageSquareText },
];

const STATUS_STYLES = {
  READY: { dot: "bg-green-400", text: "text-green-400", label: "Ready" },
  DEGRADED: { dot: "bg-yellow-400", text: "text-yellow-400", label: "Degraded" },
  NOT_FOUND: { dot: "bg-red-500", text: "text-red-500", label: "No pipeline output" },
};

function SystemBadge() {
  const { data, loading, error } = useSystemStatus();
  if (loading) return <span className="text-xs font-mono text-gray-500">checking…</span>;
  if (error || !data) {
    return (
      <span className="inline-flex items-center gap-1.5 text-xs font-mono text-red-400">
        <Radio className="w-3 h-3" /> backend unreachable
      </span>
    );
  }
  const style = STATUS_STYLES[data.pipeline_status] || STATUS_STYLES.NOT_FOUND;
  return (
    <span className={`inline-flex items-center gap-1.5 text-xs font-mono ${style.text}`}>
      <span className={`w-2 h-2 rounded-full animate-pulse ${style.dot}`} />
      {style.label}
    </span>
  );
}

export default function Layout() {
  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 flex">
      {/* Sidebar */}
      <aside className="w-56 shrink-0 border-r border-gray-800 bg-gray-900 flex flex-col">
        <div className="px-4 py-4 border-b border-gray-800">
          <div className="text-amber-400 font-bold text-base tracking-tight">
            🚦 ParkSight AI
          </div>
          <div className="text-[10px] font-mono uppercase tracking-widest text-gray-500 mt-0.5">
            Traffic Ops Intelligence
          </div>
        </div>

        <nav className="flex-1 px-2 py-3 space-y-0.5 overflow-y-auto">
          {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-all duration-150 ${
                  isActive
                    ? "bg-amber-400/15 text-amber-400 font-semibold"
                    : "text-gray-400 hover:bg-gray-800 hover:text-gray-100"
                }`
              }
            >
              <Icon className="w-4 h-4 shrink-0" />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="px-4 py-3 border-t border-gray-800">
          <SystemBadge />
        </div>
      </aside>

      {/* Main content — NO max-width so map can fill screen */}
      <main className="flex-1 min-w-0 overflow-auto">
        <Outlet />
      </main>
    </div>
  );
}