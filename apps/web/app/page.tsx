import { ArrowRight, Database, Fingerprint, Sparkles } from "lucide-react";
import Link from "next/link";

import { SiteHeader } from "@/components/site-header";

export default function HomePage() {
  return (
    <div className="landing-page">
      <SiteHeader />
      <main>
        <section className="landing-hero">
          <div className="hero-copy">
            <p className="eyebrow">PROVENANCE-BACKED GAMEPLAY SOUND</p>
            <h1>
              YOUR GAME
              <br />
              ALREADY <span>MOVES.</span>
              <br />
              LET IT HIT.
            </h1>
            <p className="hero-deck">
              Upload a silent gameplay clip. Mark the moments that matter. Generate, inspect,
              approve, and export a provenance-backed sound kit.
            </p>
            <div className="hero-actions">
              <Link href="/projects/new?source=demo" className="button button-primary">
                SOUND THE DEMO CLIP <ArrowRight size={18} aria-hidden="true" />
              </Link>
              <Link href="/projects/new?source=upload" className="button button-ghost">
                UPLOAD MY CLIP
              </Link>
            </div>
            <p className="microcopy">3 events · 2 candidates each · private project storage</p>
          </div>

          <div className="hero-machine" aria-label="A stylized sound-editing timeline">
            <div className="machine-topline">
              <span>JELLY_RELAY.MP4</span>
              <span>00:12:00 / 30 FPS</span>
            </div>
            <div className="machine-stage">
              <div className="moon" />
              <div className="jelly" aria-hidden="true">
                <span />
                <span />
              </div>
              <div className="platform platform-one" />
              <div className="platform platform-two" />
              <div className="route-crystal" />
              <div className="scanline" />
            </div>
            <div className="machine-waveform" aria-hidden="true">
              {Array.from({ length: 68 }, (_, index) => (
                <i
                  key={index}
                  style={{ height: `${10 + ((index * 37) % 54)}%` }}
                  className={index > 13 && index < 19 ? "hot" : ""}
                />
              ))}
              <span className="playhead" />
            </div>
            <div className="machine-events">
              <span>01 / GLASS LANDING</span>
              <span>02 / BUBBLE POP</span>
              <span>03 / ROUTE CONFIRM</span>
            </div>
          </div>
        </section>

        <section className="trust-strip" aria-label="Production infrastructure">
          <article>
            <Sparkles size={22} aria-hidden="true" />
            <span>GENERATED WITH</span>
            <strong>GENBLAZE</strong>
          </article>
          <article>
            <Database size={22} aria-hidden="true" />
            <span>STORED ON</span>
            <strong>BACKBLAZE B2</strong>
          </article>
          <article>
            <Fingerprint size={22} aria-hidden="true" />
            <span>VERIFIED BY</span>
            <strong>SHA-256 PROVENANCE</strong>
          </article>
        </section>
      </main>
      <footer className="landing-footer">
        <span>FRAMEFOLEY / PHASE 1</span>
        <span>HUMAN APPROVAL REMAINS AUTHORITATIVE</span>
      </footer>
    </div>
  );
}
