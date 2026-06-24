// frontend/src/components/TimelinePlayer.jsx
/**
 * TimelinePlayer — time-scrubber that lets operators replay hotspot
 * intensity across hours of the day.
 */
import { useState, useEffect, useRef } from "react";
import { Play, Pause, SkipBack } from "lucide-react";

const HOURS = Array.from({ length: 16 }, (_, i) => {
  const h = i + 6; // 6 AM – 9 PM
  return {
    label: h < 12 ? `${h}AM` : h === 12 ? "12PM" : `${h - 12}PM`,
    hour: h,
  };
});

/**
 * Simulates intensity at a given hour for a hotspot based on peak_hour.
 * Replace with real API data when per-hour panel is available.
 */
function intensityAt(hotspot, hour) {
  const peak = hotspot.peak_hour ?? 9;
  const dist = Math.abs(hour - peak);
  const base = (hotspot.violations || 50) / 200;
  return Math.max(0, base - dist * 0.08);
}

export default function TimelinePlayer({ hotspots = [] }) {
  const [currentHour, setCurrentHour] = useState(9);
  const [playing, setPlaying] = useState(false);
  const intervalRef = useRef(null);

  useEffect(() => {
    if (playing) {
      intervalRef.current = setInterval(() => {
        setCurrentHour((h) => {
          const next = h + 1;
          if (next > 21) { setPlaying(false); return 6; }
          return next;
        });
      }, 1000);
    } else {
      clearInterval(intervalRef.current);
    }
    return () => clearInterval(intervalRef.current);
  }, [playing]);

  const hourData = hotspots.map((h) => ({
    ...h,
    intensity: intensityAt(h, currentHour),
  }));

  const activeCount = hourData.filter((h) => h.intensity > 0.3).length;

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
      <div className="flex items-center justify-between mb-3">
        <div>
          <div className="text-sm font-semibold text-gray-200">Timeline Playback</div>
          <div className="text-xs text-gray-500 font-mono">
            {HOURS.find((h) => h.hour === currentHour)?.label} — {activeCount} active hotspots
          </div>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => { setCurrentHour(6); setPlaying(false); }}
            className="p-1.5 rounded-lg bg-gray-800 text-gray-400 hover:text-gray-200 transition-colors"
          >
            <SkipBack className="w-4 h-4" />
          </button>
          <button
            onClick={() => setPlaying((p) => !p)}
            className="p-1.5 rounded-lg bg-amber-400 text-gray-950 hover:bg-amber-300 transition-colors"
          >
            {playing ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {/* Scrubber */}
      <div className="relative mb-3">
        <input
          type="range"
          min={6} max={21} value={currentHour}
          onChange={(e) => { setCurrentHour(+e.target.value); setPlaying(false); }}
          className="w-full accent-amber-400"
        />
        <div className="flex justify-between text-xs text-gray-600 font-mono mt-1">
          {HOURS.filter((_, i) => i % 3 === 0).map((h) => (
            <span key={h.hour}>{h.label}</span>
          ))}
        </div>
      </div>

      {/* Activity bars */}
      <div className="flex gap-0.5 items-end h-10">
        {HOURS.map(({ hour, label }) => {
          const totalIntensity = hotspots.reduce((s, h) => s + intensityAt(h, hour), 0);
          const height = Math.min(100, (totalIntensity / Math.max(hotspots.length, 1)) * 200);
          const isActive = hour === currentHour;
          return (
            <button
              key={hour}
              onClick={() => { setCurrentHour(hour); setPlaying(false); }}
              className="flex-1 rounded-sm transition-all"
              style={{
                height: `${Math.max(4, height)}%`,
                background: isActive ? "#f59e0b" : hour < currentHour ? "#78350f" : "#1f2937",
              }}
              title={label}
            />
          );
        })}
      </div>
    </div>
  );
}