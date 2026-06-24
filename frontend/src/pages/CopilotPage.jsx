// frontend/src/pages/CopilotPage.jsx
import { useState, useRef, useEffect } from "react";
import { PageHeader, Panel } from "../components/Panel";

const EXAMPLE_PROMPTS = [
  "Why is MG Road critical?",
  "What are the top congestion drivers today?",
  "Where should 2 additional patrol teams be deployed?",
  "Which hotspot offers the greatest congestion reduction opportunity?",
  "What is tomorrow's highest-risk area?",
  "How many critical zones are there and what should we do?",
];

function Message({ role, content, loading }) {
  return (
    <div className={`flex gap-3 ${role === "user" ? "flex-row-reverse" : "flex-row"}`}>
      <div className={`w-7 h-7 rounded-full shrink-0 flex items-center justify-center text-xs font-bold ${
        role === "user" ? "bg-amber-400 text-gray-950" : "bg-gray-700 text-gray-300"
      }`}>
        {role === "user" ? "U" : "AI"}
      </div>
      <div className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
        role === "user"
          ? "bg-amber-400/15 border border-amber-400/30 text-gray-100"
          : "bg-gray-800 border border-gray-700 text-gray-200"
      }`}>
        {loading ? (
          <span className="flex gap-1 items-center text-gray-500">
            <span className="w-1.5 h-1.5 bg-gray-500 rounded-full animate-bounce" style={{animationDelay:"0ms"}}/>
            <span className="w-1.5 h-1.5 bg-gray-500 rounded-full animate-bounce" style={{animationDelay:"150ms"}}/>
            <span className="w-1.5 h-1.5 bg-gray-500 rounded-full animate-bounce" style={{animationDelay:"300ms"}}/>
          </span>
        ) : content}
      </div>
    </div>
  );
}

async function fetchHotspotContext(apiBase) {
  try {
    const [hs, intel, econ] = await Promise.all([
      fetch(`${apiBase}/hotspots`).then((r) => r.json()),
      fetch(`${apiBase}/intelligence`).then((r) => r.json()),
      fetch(`${apiBase}/economic/summary`).then((r) => r.json()),
    ]);
    return { hotspots: hs?.items?.slice(0, 15), intelligence: intel?.items?.slice(0, 10), economic: econ };
  } catch {
    return {};
  }
}

async function askClaude(query, context) {
  const systemPrompt = `You are ParkSight AI Copilot, an expert Traffic Operations Intelligence assistant for Bengaluru city traffic authorities.

You have access to real-time parking violation and congestion data. Answer questions clearly and operationally — focus on what authorities should DO, not just what the data shows.

Current data context:
${JSON.stringify(context, null, 2)}

Rules:
- Be concise and operational. Lead with the answer, then explain.
- Always ground answers in the provided data context.
- Use specific numbers from the context when available.
- If data is insufficient, say so clearly — never invent.
- Format key recommendations clearly.`;

  const response = await fetch("https://api.anthropic.com/v1/messages", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    "x-api-key": import.meta.env.VITE_ANTHROPIC_API_KEY,
    "anthropic-version": "2023-06-01",
    "anthropic-dangerous-direct-browser-access": "true",
  },
  body: JSON.stringify({
    model: "claude-sonnet-4-6",
    max_tokens: 1000,
    system: systemPrompt,
    messages: [{ role: "user", content: query }],
  }),
});

  const data = await response.json();
  return data.content?.map((b) => b.text || "").join("") || "No response received.";
}

export default function CopilotPage() {
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content: "Hello! I'm your Traffic Operations AI Copilot. Ask me about hotspots, patrol deployment, congestion causes, or enforcement priorities. What would you like to know?",
    },
  ]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [context, setContext] = useState(null);
  const bottomRef = useRef(null);
  const apiBase = import.meta.env.VITE_API_BASE_URL;

  useEffect(() => {
    fetchHotspotContext(apiBase).then(setContext);
  }, [apiBase]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function submit(q) {
    const text = (q || query).trim();
    if (!text || loading) return;
    setQuery("");

    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setLoading(true);

    // Add loading placeholder
    setMessages((prev) => [...prev, { role: "assistant", content: "", loading: true }]);

    try {
      const answer = await askClaude(text, context || {});
      setMessages((prev) => [
        ...prev.slice(0, -1),
        { role: "assistant", content: answer },
      ]);
    } catch (e) {
      setMessages((prev) => [
        ...prev.slice(0, -1),
        { role: "assistant", content: `Error: ${e.message}. Please try again.` },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col h-screen bg-gray-950">
      <div className="shrink-0 px-6 py-4 border-b border-gray-800 bg-gray-900">
        <h1 className="text-lg font-bold text-gray-100">🤖 AI Traffic Copilot</h1>
        <p className="text-xs text-gray-500 mt-0.5">
          Natural language interface to your traffic intelligence data
          {context ? " · Context loaded" : " · Loading context…"}
        </p>
      </div>

      {/* Chat history */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
        {messages.map((m, i) => (
          <Message key={i} role={m.role} content={m.content} loading={m.loading} />
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Example prompts */}
      <div className="px-6 py-2 flex gap-2 flex-wrap border-t border-gray-800/50">
        {EXAMPLE_PROMPTS.map((p) => (
          <button
            key={p}
            onClick={() => submit(p)}
            disabled={loading}
            className="text-xs px-2.5 py-1 rounded-full border border-gray-700 text-gray-500 hover:text-amber-400 hover:border-amber-400/60 transition-colors disabled:opacity-40"
          >
            {p}
          </button>
        ))}
      </div>

      {/* Input */}
      <div className="shrink-0 px-6 py-4 border-t border-gray-800 bg-gray-900">
        <div className="flex gap-2">
          <input
            className="flex-1 bg-gray-800 border border-gray-700 rounded-xl px-4 py-3 text-sm text-gray-100 placeholder-gray-600 focus:outline-none focus:border-amber-400 transition-colors"
            placeholder="Ask about hotspots, congestion, patrol deployment…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && submit()}
            disabled={loading}
          />
          <button
            onClick={() => submit()}
            disabled={loading || !query.trim()}
            className="px-5 py-3 rounded-xl bg-amber-400 text-gray-950 font-bold text-sm hover:bg-amber-300 disabled:opacity-40 transition-colors"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}