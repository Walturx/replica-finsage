import { RotateCcw } from "lucide-react";
import { useEffect, useState } from "react";

import type { ChunkRef, Source } from "../contracts/events";
import { ChatView } from "../features/chat/ChatView";
import { useChat } from "../features/chat/useChat";
import { RecordingsList } from "../features/demo-mode/RecordingsList";
import { PdfPanel, type PdfTarget } from "../features/pdf-viewer/PdfPanel";
import { Logo } from "../shared/ui/Logo";
import { SourceBadge } from "../shared/ui/SourceBadge";

type Mode = "chat" | "recordings";

export function App() {
  const chat = useChat();
  const [mode, setMode] = useState<Mode>("chat");
  const [pdf, setPdf] = useState<PdfTarget | null>(null);
  const [backend, setBackend] = useState<Source | "offline" | null>(null);

  useEffect(() => {
    fetch("/api/health")
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then((h: { source: Source }) => setBackend(h.source), () => setBackend("offline"));
  }, []);

  const openChunk = (c: ChunkRef) => setPdf(c);
  const offline = backend === "offline";

  return (
    <div className="flex h-full min-h-0 flex-col">
      <header className="flex items-center gap-3 border-b border-border px-4 py-2.5 sm:px-6">
        <Logo />
        <nav className="ml-1 flex shrink-0 rounded-full bg-muted p-0.5 text-[12.5px] whitespace-nowrap sm:ml-4" aria-label="Mode">
          {(["chat", "recordings"] as const).map((m) => (
            <button
              key={m}
              type="button"
              onClick={() => setMode(m)}
              aria-pressed={mode === m}
              className={`cursor-pointer rounded-full px-3 py-1 transition-colors ${mode === m ? "bg-card font-medium text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"}`}
            >
              {m === "chat" ? "Ask" : (
                <>
                  <span className="sm:hidden">Recorded</span>
                  <span className="hidden sm:inline">Recorded runs</span>
                </>
              )}
            </button>
          ))}
        </nav>
        <div className="ml-auto flex items-center gap-2">
          {backend && backend !== "offline" && (
            <span className="hidden sm:inline-flex">
              <SourceBadge source={backend} />
            </span>
          )}
          {offline && <span className="text-[12px] text-bad">Backend offline</span>}
          {chat.turns.length > 0 && (
            <button
              type="button"
              onClick={chat.reset}
              disabled={chat.busy}
              className="flex cursor-pointer items-center gap-1.5 rounded-full px-2.5 py-1 text-[12.5px] text-muted-foreground transition-colors hover:bg-muted hover:text-foreground disabled:opacity-40"
            >
              <RotateCcw className="h-3.5 w-3.5" /> New chat
            </button>
          )}
        </div>
      </header>

      <div className="flex min-h-0 flex-1">
        {mode === "recordings" && (
          <aside className="w-[300px] shrink-0 overflow-y-auto border-r border-border bg-bg-alt p-3">
            <p className="m-0 mb-2 px-2.5 font-mono text-[10.5px] uppercase tracking-wide text-muted-2">Recorded runs</p>
            <RecordingsList disabled={chat.busy} onPlay={(r) => void chat.replay(r.run_id, r.question)} />
          </aside>
        )}
        <main className="flex min-w-0 flex-1 flex-col">
          <ChatView
            turns={chat.turns}
            busy={chat.busy}
            composerDisabled={offline || mode === "recordings"}
            composerNote={mode === "recordings" ? "Replaying recorded runs. Switch to Ask to send a new question." : undefined}
            onSend={(text) => void chat.send(text)}
            onStop={chat.stop}
            onOpenCitation={setPdf}
            onOpenChunk={openChunk}
          />
        </main>
        {pdf && (
          <div className="hidden w-[min(46%,640px)] shrink-0 md:flex">
            <PdfPanel target={pdf} onClose={() => setPdf(null)} />
          </div>
        )}
      </div>
      {pdf && (
        <div className="fixed inset-0 z-20 flex md:hidden">
          <PdfPanel target={pdf} onClose={() => setPdf(null)} />
        </div>
      )}
    </div>
  );
}
