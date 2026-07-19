import Link from "next/link";

export function Wordmark() {
  return (
    <span className="wordmark" aria-label="FRAMEFOLEY">
      <span className="wordmark-frame">FRAME</span>
      <span className="wordmark-cut" aria-hidden="true" />
      <span>FOLEY</span>
    </span>
  );
}

export function SiteHeader({ compact = false }: { compact?: boolean }) {
  return (
    <header className={`site-header ${compact ? "site-header-compact" : ""}`}>
      <Link href="/" className="logo-link">
        <Wordmark />
      </Link>
      <div className="header-signal" aria-label="Service design principles">
        <span className="signal-dot" aria-hidden="true" />
        <span>GENBLAZE / B2 / SHA-256</span>
      </div>
    </header>
  );
}
