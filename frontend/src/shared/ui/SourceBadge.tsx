import type { Source } from "../../contracts/events";

const LABELS: Record<Source, { text: string; className: string }> = {
  live: { text: "Live pipeline", className: "bg-accent-soft text-accent" },
  recording: { text: "Recorded run", className: "bg-muted text-ink-2" },
  dev: { text: "Dev fixture", className: "bg-warn-soft text-warn" },
};

export function SourceBadge({ source }: { source: Source }) {
  const { text, className } = LABELS[source];
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 font-mono text-[10.5px] uppercase tracking-wide ${className}`}>
      {text}
    </span>
  );
}
