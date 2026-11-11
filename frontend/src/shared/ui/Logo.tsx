/** Ledger mark: three filing rows, the middle one ending in an evidence dot. */
export function LogoMark({ size = 26 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden="true">
      <rect width="32" height="32" rx="8" fill="var(--mark-bg)" />
      <rect x="8" y="9" width="16" height="2.5" rx="1.25" fill="var(--mark-fg)" />
      <rect x="8" y="14.75" width="10" height="2.5" rx="1.25" fill="var(--mark-fg)" />
      <circle cx="22.25" cy="16" r="2.25" fill="var(--accent)" />
      <rect x="8" y="20.5" width="13" height="2.5" rx="1.25" fill="var(--mark-fg)" opacity="0.55" />
    </svg>
  );
}

export function Logo() {
  return (
    <div className="flex items-center gap-2.5">
      <LogoMark />
      <div className="flex items-baseline gap-2">
        <span className="text-[15px] font-semibold tracking-tight">FinSage</span>
        <span className="hidden font-mono text-[10.5px] uppercase tracking-[0.12em] text-muted-foreground sm:inline">replica</span>
      </div>
    </div>
  );
}
