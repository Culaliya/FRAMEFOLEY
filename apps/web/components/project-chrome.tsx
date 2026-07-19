import type { FrameFoleyProject } from "@framefoley/contracts";
import Link from "next/link";

import { SiteHeader } from "@/components/site-header";

const PHASES = ["source", "cue", "generate", "audition", "render", "export"] as const;

const LABELS: Record<(typeof PHASES)[number], string> = {
  source: "SOURCE",
  cue: "CUE",
  generate: "GENERATE",
  audition: "AUDITION",
  render: "MIX",
  export: "EXPORT",
};

export function ProjectChrome({
  project,
  active,
  children,
}: {
  project: FrameFoleyProject;
  active: (typeof PHASES)[number];
  children: React.ReactNode;
}) {
  const activeIndex = PHASES.indexOf(active);
  return (
    <div className="project-page">
      <SiteHeader compact />
      <nav className="phase-rail" aria-label="Project phases">
        <div className="project-identity">
          <span className="eyebrow">{project.evidenceLabel ?? "PRIVATE PROJECT"}</span>
          <strong>{project.title}</strong>
        </div>
        <ol>
          {PHASES.map((phase, index) => {
            const isCurrent = phase === active;
            const isPast = index < activeIndex || project.state === "complete";
            return (
              <li key={phase} data-state={isCurrent ? "active" : isPast ? "past" : "future"}>
                <span>{String(index + 1).padStart(2, "0")}</span>
                <span>{LABELS[phase]}</span>
              </li>
            );
          })}
        </ol>
        <Link href="/projects/new" className="phase-new-link">
          NEW PROJECT ↗
        </Link>
      </nav>
      <main className="project-main">{children}</main>
    </div>
  );
}

export function ProjectLoading() {
  return (
    <main className="center-state" aria-live="polite">
      <span className="loader-rail" aria-hidden="true" />
      <p className="eyebrow">RECOVERING PROJECT.JSON</p>
      <h1>Loading the edit.</h1>
    </main>
  );
}

export function ProjectError({ message }: { message: string }) {
  return (
    <main className="center-state error-state" role="alert">
      <p className="eyebrow coral">PRIVATE LINK UNAVAILABLE</p>
      <h1>This cut cannot be opened.</h1>
      <p>{message}</p>
      <Link href="/projects/new" className="button button-primary">
        START A NEW PROJECT
      </Link>
    </main>
  );
}
