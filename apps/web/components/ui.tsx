import { Check, Database, ShieldCheck } from "lucide-react";

import { shortHash } from "@/lib/format";

export function StatusStamp({
  label,
  tone = "lime",
  icon = "check",
}: {
  label: string;
  tone?: "lime" | "cyan" | "coral" | "steel";
  icon?: "check" | "storage" | "shield";
}) {
  const Icon = icon === "storage" ? Database : icon === "shield" ? ShieldCheck : Check;
  return (
    <span className={`status-stamp status-${tone}`}>
      <Icon size={13} strokeWidth={2.4} aria-hidden="true" />
      {label}
    </span>
  );
}

export function HashValue({ value, label = "SHA-256" }: { value?: string; label?: string }) {
  return (
    <span className="hash-value" title={value}>
      <span>{label}</span>
      <code>{shortHash(value)}</code>
    </span>
  );
}

export function InlineError({ message }: { message: string | null }) {
  if (!message) return null;
  return (
    <div className="inline-error" role="alert">
      <strong>THE EDIT STOPPED</strong>
      <span>{message}</span>
    </div>
  );
}

export function PageIntro({
  step,
  title,
  copy,
}: {
  step: string;
  title: string;
  copy: string;
}) {
  return (
    <header className="page-intro">
      <p className="eyebrow">{step}</p>
      <h1>{title}</h1>
      <p>{copy}</p>
    </header>
  );
}
