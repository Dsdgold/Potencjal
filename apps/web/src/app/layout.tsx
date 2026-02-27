import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SIG Potencjał - Company Intelligence",
  description: "Credit risk scoring, company data aggregation, and material recommendations",
  manifest: "/manifest.json",
  themeColor: "#e63946",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pl">
      <body className="min-h-screen bg-sig-bg text-sig-text antialiased">
        {children}
      </body>
    </html>
  );
}
