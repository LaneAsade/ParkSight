/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        // "Obsidian Flare" — deep charcoal/black surfaces with a glowing
        // flare-orange accent. Kept under the `ink` key so every existing
        // component (Panel, KpiCard, tables, etc.) repaints automatically.
        ink: {
          950: "#0A0A0A",
          900: "#131314",
          800: "#1C1C1E",
          700: "#27272A",
          600: "#3A393A",
          500: "#52525B",
        },
        paper: {
          100: "#F5F5F6",
          300: "#C7C7CC",
          500: "#A1A1AA",
        },
        amber: {
          400: "#FF3B00",
          500: "#E03400",
        },
        flare: {
          DEFAULT: "#FF3B00",
          glow: "rgba(255, 59, 0, 0.4)",
        },
        evidence: {
          real: "#10B981",
          modeled: "#5FA8D3",
          partial: "#F59E0B",
          spec: "#52525B",
        },
        tier: {
          critical: "#EF4444",
          high: "#F59E0B",
          medium: "#E9C46A",
          low: "#5FA8D3",
        },
      },
      fontFamily: {
        display: ["'Sora'", "sans-serif"],
        body: ["'Inter'", "sans-serif"],
        mono: ["'JetBrains Mono'", "ui-monospace", "monospace"],
      },
      boxShadow: {
        glow: "0 0 20px rgba(255, 59, 0, 0.2)",
        "glow-sm": "0 0 10px rgba(255, 59, 0, 0.25)",
      },
    },
  },
  plugins: [],
};
