/** Ledger mark: three filing rows, the middle one ending in an evidence dot. Used as favicon and compact logo. */
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

/**
 * "FinSage" wordmark in a geometric display face. The dot of the i is the evidence dot from the mark,
 * and "Sage" carries the brand gradient.
 */
export function Wordmark({ size = 22 }: { size?: number }) {
  return (
    <span
      role="img"
      aria-label="FinSage"
      className="inline-flex select-none items-baseline font-display font-semibold leading-none tracking-[-0.02em]"
      style={{ fontSize: size }}
    >
      <span aria-hidden>F</span>
      <span aria-hidden className="relative">
        ı
        <span
          className="absolute left-1/2 rounded-full bg-accent"
          style={{ width: size * 0.2, height: size * 0.2, top: -size * 0.02, transform: "translateX(-50%)" }}
        />
      </span>
      <span aria-hidden>n</span>
      <span aria-hidden className="brand-gradient">
        Sage
      </span>
    </span>
  );
}
