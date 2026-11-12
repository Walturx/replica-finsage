import { Menu } from "lucide-react";
import { useEffect, useState } from "react";

import type { Source } from "../contracts/events";
import { ChatView } from "../features/chat/ChatView";
import { useChat } from "../features/chat/useChat";
import { useScope } from "../features/document/useScope";
import { PdfPanel, type PdfTarget } from "../features/pdf-viewer/PdfPanel";
import { useTheme } from "../shared/theme/useTheme";
import { Wordmark } from "../shared/ui/Logo";
import { Sidebar } from "./Sidebar";

export function App() {
  const chat = useChat();
  const scope = useScope();
  const theme = useTheme();
  const [pdf, setPdf] = useState<PdfTarget | null>(null);
  const [backend, setBackend] = useState<Source | "offline" | null>(null);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    fetch("/api/health")
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then((h: { source: Source }) => setBackend(h.source), () => setBackend("offline"));
  }, []);

  const offline = backend === "offline";
  const doc = scope.status === "ready" ? scope.scope : null;

  const sidebar = (onClose?: () => void) => (
    <Sidebar
      scope={scope}
      backend={backend}
      busy={chat.busy}
      theme={theme.choice}
      onTheme={theme.setChoice}
      onNewChat={() => {
        chat.reset();
        setPdf(null);
        onClose?.();
      }}
      onAsk={(q) => {
        void chat.send(q);
        onClose?.();
      }}
      onOpenFiling={(doc_name) => {
        setPdf({ doc_name, page_index: 0 });
        onClose?.();
      }}
      onReplay={(r) => {
        void chat.replay(r.run_id, r.question);
        onClose?.();
      }}
      onClose={onClose}
    />
  );

  return (
    <div className="flex h-full min-h-0">
      <div className="hidden shrink-0 md:flex">{sidebar()}</div>

      {menuOpen && (
        <div className="fixed inset-0 z-30 flex md:hidden">
          <div className="flex">{sidebar(() => setMenuOpen(false))}</div>
          <button type="button" aria-label="Close menu" className="flex-1 bg-black/30" onClick={() => setMenuOpen(false)} />
        </div>
      )}

      <main className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center gap-3 border-b border-border px-4 py-2.5 md:hidden">
          <button
            type="button"
            onClick={() => setMenuOpen(true)}
            aria-label="Open menu"
            className="flex h-8 w-8 cursor-pointer items-center justify-center rounded-md text-muted-foreground hover:bg-muted"
          >
            <Menu className="h-4 w-4" />
          </button>
          <Wordmark size={18} />
        </header>
        <ChatView
          turns={chat.turns}
          busy={chat.busy}
          docTitle={doc?.title}
          examples={doc?.questions.slice(0, 4).map((q) => q.question) ?? []}
          composerDisabled={offline}
          composerNote={offline ? "The backend is offline. Start it with: uv run python -m finsage_replica.api" : undefined}
          onSend={(text) => void chat.send(text)}
          onStop={chat.stop}
          onOpenCitation={setPdf}
          onOpenChunk={setPdf}
        />
      </main>

      {pdf && (
        <div className="hidden w-[min(44%,620px)] shrink-0 lg:flex">
          <PdfPanel target={pdf} onClose={() => setPdf(null)} />
        </div>
      )}
      {pdf && (
        <div className="fixed inset-0 z-20 flex lg:hidden">
          <PdfPanel target={pdf} onClose={() => setPdf(null)} />
        </div>
      )}
    </div>
  );
}
