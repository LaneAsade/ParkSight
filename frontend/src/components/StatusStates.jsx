import { AlertTriangle, Inbox, Loader2 } from "lucide-react";

export function LoadingState({ label = "Loading…" }) {
  return (
    <div className="flex items-center gap-2 py-12 justify-center text-paper-500 font-data text-sm">
      <Loader2 className="w-4 h-4 animate-spin" />
      {label}
    </div>
  );
}

/**
 * ErrorState — speaks in the interface's voice about what failed, and
 * whether it's a required artifact (the run can't be trusted yet) or an
 * optional one (this panel just has nothing to show).
 */
export function ErrorState({ error, onRetry }) {
  const code = error?.code;
  const isMissingRequired = code === "MISSING_ARTIFACT" && error?.required;
  const title = isMissingRequired
    ? "Pipeline output not found"
    : "Couldn't load this data";
  const message =
    error?.message ||
    (error?.status === 0
      ? "The backend isn't reachable. Confirm it's running and VITE_API_BASE_URL is correct."
      : "An unexpected error occurred while contacting the backend.");

  return (
    <div className="flex flex-col items-center gap-3 py-12 px-6 text-center">
      <AlertTriangle className="w-6 h-6 text-amber-400" />
      <div className="font-display text-sm text-paper-100">{title}</div>
      <div className="text-xs text-paper-500 max-w-md font-data">{message}</div>
      {error?.artifact && (
        <div className="text-xs text-paper-500 font-data">
          Missing artifact: <span className="text-amber-400">{error.artifact}</span>
        </div>
      )}
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-1 text-xs px-3 py-1.5 rounded-full border border-ink-500 text-paper-100 hover:border-amber-400 hover:text-amber-400 transition-colors"
        >
          Retry
        </button>
      )}
    </div>
  );
}

export function EmptyState({ title = "Nothing here yet", hint }) {
  return (
    <div className="flex flex-col items-center gap-2 py-12 text-center text-paper-500">
      <Inbox className="w-5 h-5" />
      <div className="text-sm font-display text-paper-300">{title}</div>
      {hint && <div className="text-xs font-data max-w-sm">{hint}</div>}
    </div>
  );
}
