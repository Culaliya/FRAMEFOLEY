import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "FRAMEFOLEY — Provenance-backed gameplay sound kits",
  description:
    "Mark gameplay moments, generate two sound candidates, inspect technical QC, and export a provenance-backed sound kit.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" data-scroll-behavior="smooth">
      <body>{children}</body>
    </html>
  );
}
