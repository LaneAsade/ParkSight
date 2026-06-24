/**
 * EvidenceChip — the console's signature element. Every figure that came
 * from a pipeline artifact is rendered next to a small chip naming its
 * validation_status, so nobody can mistake a MODELED projection for a
 * REAL_DATA measurement.
 */
const LABELS = {
  REAL_DATA: { text: "Real data", color: "var(--evidence-real)" },
  MODELED: { text: "Modeled", color: "var(--evidence-modeled)" },
  PARTIAL: { text: "Partial", color: "var(--evidence-partial)" },
  SPEC_ONLY: { text: "Unavailable", color: "var(--evidence-spec)" },
};

export default function EvidenceChip({ status, title }) {
  const meta = LABELS[status] || LABELS.SPEC_ONLY;
  return (
    <span
      className="provenance-chip"
      style={{ color: meta.color }}
      title={title || `Validation status: ${status || "SPEC_ONLY"}`}
    >
      <span className="provenance-dot" aria-hidden="true" />
      {meta.text}
    </span>
  );
}
