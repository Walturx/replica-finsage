import * as pdfjs from "pdfjs-dist";
import workerUrl from "pdfjs-dist/build/pdf.worker.min.mjs?url";
import { ChevronLeft, ChevronRight, Loader2, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";

pdfjs.GlobalWorkerOptions.workerSrc = workerUrl;

export interface PdfTarget {
  doc_name: string;
  page_index: number;
  section?: string;
  snippet?: string;
}

/** Side panel that opens the cited filing on the cited page. */
export function PdfPanel({ target, onClose }: { target: PdfTarget; onClose: () => void }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [doc, setDoc] = useState<pdfjs.PDFDocumentProxy | null>(null);
  const [page, setPage] = useState(target.page_index + 1);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");

  useEffect(() => setPage(target.page_index + 1), [target]);

  useEffect(() => {
    let cancelled = false;
    setState("loading");
    setDoc(null);
    const task = pdfjs.getDocument({ url: `/api/pdfs/${encodeURIComponent(target.doc_name)}.pdf` });
    task.promise.then(
      (loaded) => !cancelled && setDoc(loaded),
      () => !cancelled && setState("error"),
    );
    return () => {
      cancelled = true;
      void task.destroy();
    };
  }, [target.doc_name]);

  useEffect(() => {
    if (!doc || !canvasRef.current) return;
    let cancelled = false;
    let renderTask: ReturnType<pdfjs.PDFPageProxy["render"]> | null = null;
    setState("loading");
    doc.getPage(page).then((p) => {
      if (cancelled || !canvasRef.current) return;
      const canvas = canvasRef.current;
      const width = canvas.parentElement?.clientWidth ?? 560;
      const base = p.getViewport({ scale: 1 });
      const ratio = window.devicePixelRatio || 1;
      const viewport = p.getViewport({ scale: (width / base.width) * ratio });
      canvas.width = viewport.width;
      canvas.height = viewport.height;
      canvas.style.width = `${viewport.width / ratio}px`;
      renderTask = p.render({ canvas, canvasContext: canvas.getContext("2d")!, viewport });
      renderTask.promise.then(
        () => !cancelled && setState("ready"),
        () => !cancelled && setState("error"),
      );
    });
    return () => {
      cancelled = true;
      renderTask?.cancel();
    };
  }, [doc, page]);

  const total = doc?.numPages ?? 0;
  const isCited = page === target.page_index + 1;

  return (
    <aside className="flex h-full min-h-0 w-full flex-col border-l border-border bg-bg-alt">
      <header className="flex items-center gap-2 border-b border-border px-4 py-3">
        <div className="min-w-0 flex-1">
          <p className="m-0 truncate text-[13px] font-medium">{target.doc_name.replaceAll("_", " ")}</p>
          <p className="m-0 truncate text-[11.5px] text-muted-foreground">{target.section ?? "Source document"}</p>
        </div>
        <button
          type="button"
          onClick={() => setPage((p) => Math.max(1, p - 1))}
          disabled={page <= 1}
          aria-label="Previous page"
          className="flex h-7 w-7 cursor-pointer items-center justify-center rounded-md text-muted-foreground hover:bg-muted disabled:opacity-30"
        >
          <ChevronLeft className="h-4 w-4" />
        </button>
        <span className="min-w-[72px] text-center font-mono text-[11.5px] tabular-nums text-ink-2">
          p. {page}
          {total ? ` / ${total}` : ""}
        </span>
        <button
          type="button"
          onClick={() => setPage((p) => Math.min(total || p, p + 1))}
          disabled={!total || page >= total}
          aria-label="Next page"
          className="flex h-7 w-7 cursor-pointer items-center justify-center rounded-md text-muted-foreground hover:bg-muted disabled:opacity-30"
        >
          <ChevronRight className="h-4 w-4" />
        </button>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close document"
          className="flex h-7 w-7 cursor-pointer items-center justify-center rounded-md text-muted-foreground hover:bg-muted"
        >
          <X className="h-4 w-4" />
        </button>
      </header>

      {target.snippet && (
        <div className="border-b border-border px-4 py-3">
          <p className="m-0 mb-1 font-mono text-[10.5px] uppercase tracking-wide text-muted-2">
            {isCited ? "Cited excerpt" : `Cited excerpt is on page ${target.page_index + 1}`}
          </p>
          <pre className="m-0 max-h-28 overflow-auto whitespace-pre-wrap rounded-lg border-l-2 border-accent bg-card px-3 py-2 font-mono text-[11px] leading-relaxed text-ink-2">
            {target.snippet}
          </pre>
        </div>
      )}

      <div className="relative min-h-0 flex-1 overflow-auto p-4">
        {state === "loading" && (
          <div className="absolute inset-0 flex items-center justify-center text-muted-foreground">
            <Loader2 className="h-5 w-5 animate-spin" aria-label="Loading page" />
          </div>
        )}
        {state === "error" ? (
          <p role="alert" className="m-0 text-[12.5px] text-bad">
            Could not open this document. Check that the backend is running and the PDF exists in data/financebench/pdfs.
          </p>
        ) : (
          <div className={`overflow-hidden rounded-md bg-white shadow-sm ${isCited ? "ring-2 ring-accent/60" : ""}`}>
            <canvas ref={canvasRef} className="block max-w-full" />
          </div>
        )}
      </div>
    </aside>
  );
}
