import { FileText, Monitor, Moon, SquarePen, Sun, X } from "lucide-react";
import type { ReactNode } from "react";

import type { Source } from "../contracts/events";
import { RecordingsList, type RecordingInfo } from "../features/demo-mode/RecordingsList";
import type { ScopeState } from "../features/document/useScope";
import type { ThemeChoice } from "../shared/theme/useTheme";
import { Wordmark } from "../shared/ui/Logo";
import { SourceBadge } from "../shared/ui/SourceBadge";

interface Props {
  scope: ScopeState;
  backend: Source | "offline" | null;
  busy: boolean;
  theme: ThemeChoice;
  onTheme: (t: ThemeChoice) => void;
  onNewChat: () => void;
  onAsk: (question: string) => void;
  onOpenFiling: (docName: string) => void;
  onReplay: (r: RecordingInfo) => void;
  onClose?: () => void;
}

const SectionLabel = ({ children }: { children: ReactNode }) => (
  <div className="px-2.5 pb-1 pt-4 text-[11px] font-semibold whitespace-nowrap text-muted-foreground">{children}</div>
);

const THEMES: { value: ThemeChoice; label: string; Icon: typeof Sun }[] = [
  { value: "light", label: "Light theme", Icon: Sun },
  { value: "dark", label: "Dark theme", Icon: Moon },
  { value: "system", label: "Follow system theme", Icon: Monitor },
];

export function Sidebar({ scope, backend, busy, theme, onTheme, onNewChat, onAsk, onOpenFiling, onReplay, onClose }: Props) {
  return (
    <nav aria-label="Sidebar" className="flex h-full w-[264px] flex-col border-r border-border bg-side">
      <div className="flex items-center justify-between px-4 pb-2 pt-4">
        <Wordmark size={21} />
        {onClose && (
          <button
            type="button"
            onClick={onClose}
            aria-label="Close menu"
            className="flex h-8 w-8 cursor-pointer items-center justify-center rounded-md text-muted-foreground hover:bg-muted"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>

      <div className="px-2">
        <button
          type="button"
          onClick={onNewChat}
          disabled={busy}
          className="flex w-full cursor-pointer items-center gap-2.5 rounded-lg px-2.5 py-2 text-[13.5px] text-foreground transition-colors hover:bg-muted disabled:opacity-40"
        >
          <SquarePen className="h-4 w-4" /> New chat
        </button>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-2 pb-3">
        <SectionLabel>Document in scope</SectionLabel>
        {scope.status === "ready" ? (
          <div className="mx-0.5 rounded-xl border border-border bg-card p-3 shadow-card">
            <div className="flex items-start gap-2.5">
              <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-accent-soft text-accent">
                <FileText className="h-3.5 w-3.5" />
              </span>
              <div className="min-w-0">
                <p className="m-0 truncate text-[13px] font-medium">{scope.scope.title}</p>
                <p className="m-0 text-[11.5px] text-muted-foreground">
                  {scope.scope.page_count ? `${scope.scope.page_count} pages · ` : ""}
                  {scope.scope.questions.length} FinanceBench questions
                </p>
              </div>
            </div>
            <button
              type="button"
              onClick={() => onOpenFiling(scope.scope.doc_name)}
              className="mt-2.5 w-full cursor-pointer rounded-lg border border-border px-2 py-1.5 text-[12px] text-ink-2 transition-colors hover:border-border-strong hover:bg-muted"
            >
              Open filing
            </button>
          </div>
        ) : (
          <p className="m-0 px-2.5 text-[12px] text-muted-foreground">
            {scope.status === "loading" ? "Loading document" : "No document configured. Check that the backend is running."}
          </p>
        )}

        {scope.status === "ready" && scope.scope.questions.length > 0 && (
          <>
            <SectionLabel>Benchmark questions</SectionLabel>
            <ul className="m-0 flex list-none flex-col p-0">
              {scope.scope.questions.map((q) => (
                <li key={q.id}>
                  <button
                    type="button"
                    disabled={busy || backend === "offline"}
                    onClick={() => onAsk(q.question)}
                    title={q.question}
                    className="w-full cursor-pointer rounded-lg px-2.5 py-1.5 text-left text-[13px] text-ink-2 transition-colors hover:bg-muted disabled:cursor-default disabled:opacity-50"
                  >
                    <span className="line-clamp-2">{q.question}</span>
                  </button>
                </li>
              ))}
            </ul>
          </>
        )}

        <SectionLabel>Recorded runs</SectionLabel>
        <div className="px-0.5">
          <RecordingsList disabled={busy} onPlay={onReplay} />
        </div>
      </div>

      <div className="flex flex-col gap-2.5 border-t border-border px-4 py-3">
        <div className="flex items-center justify-between gap-2">
          {backend && backend !== "offline" ? (
            <SourceBadge source={backend} />
          ) : (
            <span className="text-[11.5px] text-bad">{backend === "offline" ? "Backend offline" : ""}</span>
          )}
          <div className="flex rounded-full bg-muted p-0.5" role="group" aria-label="Theme">
            {THEMES.map(({ value, label, Icon }) => (
              <button
                key={value}
                type="button"
                onClick={() => onTheme(value)}
                aria-label={label}
                aria-pressed={theme === value}
                className={`flex h-6 w-6 cursor-pointer items-center justify-center rounded-full transition-colors ${theme === value ? "bg-card text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"}`}
              >
                <Icon className="h-3.5 w-3.5" />
              </button>
            ))}
          </div>
        </div>
        <p className="m-0 text-[11px] leading-snug text-muted-2">
          Replication of FinSage (Wang et al., CIKM 2025) for a single FinanceBench filing.
        </p>
      </div>
    </nav>
  );
}
