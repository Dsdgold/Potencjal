"use client";

import { useAuth } from "@/lib/auth";
import { subscriptionsApi } from "@/lib/api";
import { useState } from "react";

export default function SettingsPage() {
  const { user, token } = useAuth();
  const [portalLoading, setPortalLoading] = useState(false);

  const openPortal = async () => {
    setPortalLoading(true);
    try {
      const result = await subscriptionsApi.portal(token!);
      window.open(result.portal_url, "_blank");
    } catch {
      alert("Brak aktywnej subskrypcji Stripe");
    }
    setPortalLoading(false);
  };

  return (
    <div className="max-w-2xl space-y-6 animate-fade-in">
      <h1 className="text-xl font-bold">Ustawienia</h1>

      <div className="bg-sig-card border border-sig-border rounded-2xl p-6 space-y-4">
        <h2 className="text-sm font-bold text-sig-red">Profil</h2>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div><span className="text-sig-muted">Email:</span> {user?.email}</div>
          <div><span className="text-sig-muted">Imię:</span> {user?.full_name}</div>
          <div><span className="text-sig-muted">Rola:</span> {user?.role}</div>
          <div><span className="text-sig-muted">Organizacja:</span> {user?.org_name || "—"}</div>
        </div>
      </div>

      <div className="bg-sig-card border border-sig-border rounded-2xl p-6 space-y-4">
        <h2 className="text-sm font-bold text-sig-red">Subskrypcja</h2>
        <p className="text-sm text-sig-muted">
          Zarządzaj swoim planem i płatnościami przez portal Stripe.
        </p>
        <button onClick={openPortal} disabled={portalLoading}
          className="px-4 py-2 bg-sig-red hover:bg-sig-red-dark disabled:opacity-50 rounded-lg text-sm font-bold text-white transition">
          {portalLoading ? "Otwieranie..." : "Zarządzaj subskrypcją"}
        </button>
      </div>

      <div className="bg-sig-card border border-sig-border rounded-2xl p-6 space-y-4">
        <h2 className="text-sm font-bold text-sig-red">GDPR / RODO</h2>
        <p className="text-sm text-sig-muted">
          Dane firm pobierane są z publicznych rejestrów państwowych (Biała Lista VAT, KRS, REGON, CEIDG).
          Przetwarzanie odbywa się w celach oceny ryzyka kredytowego (art. 6 ust. 1 lit. f RODO).
        </p>
        <div className="flex gap-3">
          <button className="px-4 py-2 bg-sig-surface border border-sig-border rounded-lg text-sm hover:border-sig-red/30 transition">
            Eksportuj dane organizacji
          </button>
          <button className="px-4 py-2 bg-sig-surface border border-sig-border rounded-lg text-sm hover:border-sig-red/30 transition text-red-400">
            Usuń konto
          </button>
        </div>
      </div>
    </div>
  );
}
