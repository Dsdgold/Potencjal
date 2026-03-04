import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "BuildLeads — Platforma oceny potencjału B2B",
  description: "Scoring leadów, OSINT, analiza potencjału klientów w branży budowlanej",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="pl">
      <body className="antialiased bg-[#020709] text-[#e8edf2]">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
