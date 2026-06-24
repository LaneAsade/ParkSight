/**
 * Panel — the standard content card used to wrap every chart/table on every
 * page, so the console has one consistent container instead of each page
 * re-inventing borders/padding.
 */
export function Panel({ title, action, children, className = "" }) {
  return (
    <div className={`flare-card rounded-xl ${className}`}>
      {(title || action) && (
        <div className="flex items-center justify-between px-4 py-3 border-b border-ink-700">
          {title && <h2 className="font-display text-sm font-semibold text-paper-100">{title}</h2>}
          {action}
        </div>
      )}
      <div className="p-4">{children}</div>
    </div>
  );
}

export function PageHeader({ title, subtitle, action }) {
  return (
    <div className="flex items-start justify-between gap-4 mb-6">
      <div>
        <h1 className="font-display text-xl font-bold tracking-tight text-paper-100">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-paper-500 max-w-2xl">{subtitle}</p>}
      </div>
      {action}
    </div>
  );
}
