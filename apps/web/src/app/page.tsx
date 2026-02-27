"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { subscriptionsApi } from "@/lib/api";

export default function LandingPage() {
  const [plans, setPlans] = useState<any[]>([]);
  useEffect(() => { subscriptionsApi.plans().then(setPlans).catch(() => {}); }, []);

  return (
    <div className="min-h-screen bg-sig-bg">
      {/* Navbar */}
      <nav className="border-b border-sig-border bg-sig-surface/80 backdrop-blur sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-2xl font-black text-sig-red tracking-wider">SIG</span>
            <span className="text-lg font-semibold">Potencjał</span>
          </div>
          <div className="flex gap-3">
            <Link href="/auth/login" className="px-4 py-2 rounded-lg text-sm font-medium text-sig-muted hover:text-white transition">
              Zaloguj
            </Link>
            <Link href="/auth/register" className="px-4 py-2 bg-sig-red hover:bg-sig-red-dark rounded-lg text-sm font-bold text-white transition">
              Załóż konto
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="max-w-6xl mx-auto px-4 pt-20 pb-16 text-center">
        <h1 className="text-5xl md:text-6xl font-black leading-tight mb-6">
          Inteligencja kredytowa<br/>
          <span className="text-sig-red">dla firm budowlanych</span>
        </h1>
        <p className="text-xl text-sig-muted max-w-2xl mx-auto mb-10">
          Wpisz NIP — w sekundę otrzymasz scoring ryzyka, sugerowany limit kredytowy
          i rekomendacje produktowe. Dane z rejestrów państwowych.
        </p>
        <div className="flex justify-center gap-4">
          <Link href="/auth/register" className="px-8 py-3 bg-sig-red hover:bg-sig-red-dark rounded-xl text-lg font-bold transition shadow-lg shadow-sig-red/20">
            Rozpocznij za darmo
          </Link>
          <Link href="/auth/login" className="px-8 py-3 bg-sig-card border border-sig-border rounded-xl text-lg font-medium hover:bg-sig-surface transition">
            Demo: demo@sig.pl
          </Link>
        </div>
      </section>

      {/* Features */}
      <section className="max-w-6xl mx-auto px-4 py-16">
        <div className="grid md:grid-cols-3 gap-8">
          {[
            { title: "Scoring 0-100", desc: "11-komponentowy algorytm scoringowy z pełną wyjaśnialnością. Status VAT, forma prawna, wiek, kapitał, branża i więcej.", icon: "📊" },
            { title: "Limit kredytowy", desc: "Automatyczna sugestia limitu z zakresem min-max, terminami płatności i rabatem handlowym.", icon: "💳" },
            { title: "Mapa materiałów", desc: "Predykcja kategorii materiałów budowlanych na podstawie PKD, przetargów i profilu firmy.", icon: "🧱" },
            { title: "Multi-rejestr", desc: "Biała Lista VAT, KRS, REGON, CEIDG — agregacja danych z wielu źródeł w jednym profilu.", icon: "🏛️" },
            { title: "CRM wbudowany", desc: "Notatki, zadania, watchlisty i alerty — wszystko przy profilu firmy.", icon: "📋" },
            { title: "API & Eksport", desc: "REST API do integracji z ERP. Eksport do CSV i PDF. Webhooks.", icon: "🔗" },
          ].map((f, i) => (
            <div key={i} className="bg-sig-card border border-sig-border rounded-2xl p-6 hover:border-sig-red/30 transition">
              <div className="text-3xl mb-3">{f.icon}</div>
              <h3 className="text-lg font-bold mb-2">{f.title}</h3>
              <p className="text-sm text-sig-muted">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Pricing */}
      <section className="max-w-6xl mx-auto px-4 py-16" id="pricing">
        <h2 className="text-3xl font-black text-center mb-12">Plany cenowe</h2>
        <div className="grid md:grid-cols-3 gap-8">
          {(plans.length ? plans : [
            { code: "free", name: "Free", price_monthly: 0, features: { basic_scoring: true, credit_limit: true }, limits: { lookups_per_month: 10 } },
            { code: "pro", name: "Pro", price_monthly: 29900, features: { basic_scoring: true, credit_limit: true, material_recommendation: true, export_pdf: true }, limits: { lookups_per_month: 200 } },
            { code: "enterprise", name: "Enterprise", price_monthly: 99900, features: { basic_scoring: true, credit_limit: true, material_recommendation: true, export_pdf: true, api_access: true }, limits: { lookups_per_month: 5000 } },
          ]).map((plan: any, i: number) => (
            <div key={plan.code} className={`bg-sig-card border rounded-2xl p-6 ${i === 1 ? 'border-sig-red ring-1 ring-sig-red/20' : 'border-sig-border'}`}>
              {i === 1 && <div className="text-xs font-bold text-sig-red mb-2 uppercase">Najpopularniejszy</div>}
              <h3 className="text-xl font-bold mb-1">{plan.name}</h3>
              <div className="text-3xl font-black mb-4">
                {plan.price_monthly === 0 ? "0 PLN" : `${(plan.price_monthly / 100).toFixed(0)} PLN`}
                <span className="text-sm font-normal text-sig-muted">/mies.</span>
              </div>
              <ul className="text-sm text-sig-muted space-y-2 mb-6">
                <li>✓ {plan.limits?.lookups_per_month || 10} zapytań/mies.</li>
                <li>✓ Scoring ryzyka</li>
                <li>✓ Limit kredytowy</li>
                {plan.features?.material_recommendation && <li>✓ Rekomendacja materiałów</li>}
                {plan.features?.export_pdf && <li>✓ Eksport PDF</li>}
                {plan.features?.api_access && <li>✓ Dostęp API</li>}
              </ul>
              <Link href="/auth/register" className={`block text-center py-2 rounded-lg font-bold transition ${i === 1 ? 'bg-sig-red hover:bg-sig-red-dark text-white' : 'bg-sig-surface border border-sig-border hover:border-sig-red/30 text-sig-text'}`}>
                Wybierz
              </Link>
            </div>
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-sig-border py-8 text-center text-sm text-sig-muted">
        <p>SIG Potencjał v1.0 — Dane z rejestrów państwowych RP i UE</p>
        <p className="mt-1">Biała Lista VAT · KRS · REGON · CEIDG</p>
      </footer>
    </div>
  );
}
