import { PlayCircle } from "lucide-react";
import { useEffect, useState } from "react";

export interface RecordingInfo {
  run_id: string;
  question: string;
  model: string;
  recorded_at: string;
}

/** Recorded real runs of the pipeline, for a demo that does not depend on the network or the GPU. */
export function RecordingsList({ disabled, onPlay }: { disabled: boolean; onPlay: (r: RecordingInfo) => void }) {
  const [items, setItems] = useState<RecordingInfo[] | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    fetch("/api/recordings")
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then(setItems, () => setFailed(true));
  }, []);

  if (failed) {
    return <p className="m-0 px-2 text-[12px] text-bad">Could not load recordings.</p>;
  }
  if (items === null) {
    return <p className="m-0 px-2 text-[12px] text-muted-foreground">Loading recordings</p>;
  }
  if (items.length === 0) {
    return (
      <p className="m-0 px-2 text-[12px] leading-relaxed text-muted-foreground">
        No recordings yet. Live runs of the real pipeline are saved here automatically, for a demo without network.
      </p>
    );
  }
  return (
    <ul className="m-0 flex list-none flex-col p-0">
      {items.map((r) => (
        <li key={r.run_id}>
          <button
            type="button"
            disabled={disabled}
            onClick={() => onPlay(r)}
            className="flex w-full cursor-pointer items-start gap-2 rounded-lg px-2 py-1.5 text-left transition-colors hover:bg-muted disabled:cursor-default disabled:opacity-50"
          >
            <PlayCircle aria-hidden className="mt-0.5 h-3.5 w-3.5 shrink-0 text-accent" />
            <span className="min-w-0">
              <span className="line-clamp-2 block text-[13px] text-ink-2">{r.question}</span>
              <span className="block font-mono text-[10.5px] text-muted-2">
                {r.recorded_at ? new Date(r.recorded_at).toLocaleString() : r.run_id}
              </span>
            </span>
          </button>
        </li>
      ))}
    </ul>
  );
}
