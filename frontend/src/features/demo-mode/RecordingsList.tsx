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
    return <p className="m-0 text-[12.5px] text-bad">Could not load recordings. Check that the backend is running.</p>;
  }
  if (items === null) {
    return <p className="m-0 text-[12.5px] text-muted-foreground">Loading recordings</p>;
  }
  if (items.length === 0) {
    return (
      <p className="m-0 text-[12.5px] leading-relaxed text-muted-foreground">
        No recordings yet. Every live run of the real pipeline is saved automatically and will appear here. Development fixtures
        are never recorded.
      </p>
    );
  }
  return (
    <ul className="m-0 flex list-none flex-col gap-1.5 p-0">
      {items.map((r) => (
        <li key={r.run_id}>
          <button
            type="button"
            disabled={disabled}
            onClick={() => onPlay(r)}
            className="flex w-full cursor-pointer items-start gap-2.5 rounded-lg px-2.5 py-2 text-left transition-colors hover:bg-muted disabled:cursor-default disabled:opacity-50"
          >
            <PlayCircle aria-hidden className="mt-0.5 h-4 w-4 shrink-0 text-accent" />
            <span className="min-w-0">
              <span className="line-clamp-2 block text-[12.5px] text-foreground">{r.question}</span>
              <span className="block font-mono text-[10.5px] text-muted-2">
                {r.model} · {r.recorded_at ? new Date(r.recorded_at).toLocaleString() : r.run_id}
              </span>
            </span>
          </button>
        </li>
      ))}
    </ul>
  );
}
