"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api";
import Link from "next/link";

interface Lead {
  id: string;
  name: string;
  nip: string;
  city: string;
  employees: number | null;
  revenue_pln: number | null;
  revenue_band: string | null;
  pkd: string | null;
  pkd_desc: string | null;
  years_active: number | null;
  vat_status: string | null;
  website: string | null;
  basket_pln: number | null;
  score: number | null;
  tier: string | null;
  annual_potential: number | null;
  notes: string | null;
  sources: string[] | null;
  created_at: string;
  updated_at: string;
}

const tierInfo: Record<string, { color: string; bg: string; action: string }> = {
  S: { color: "text-emerald-400", bg: "bg-emerald-500", action: "Priorytetowy kontakt osobisty — zadzwoń dziś!" },
  A: { color: "text-blue-400", bg: "bg-blue-500", action: "Oferta rabatu ilościowego, dostawa 24–48h" },
  B: { color: "text-amber-400", bg: "bg-amber-500", action: "Kampania remarketingowa, follow-up 7 dni" },
  C: { color: "text-slate-400", bg: "bg-slate-500", action: "Monitoruj, follow-up 30 dni" },
};

export default function LeadDetailPage() {
  const { id } = useParams();
  const router = useRouter();
  const [lead, setLead] = useState<Lead | null>(null);
  const [loading, setLoading] = useState(true);
  const [scoring, setScoring] = useState(false);

  useEffect(() => {
    async function load() {
      const res = await apiFetch(`/api/v1/leads/${id}`);
      if (res.ok) setLead(await res.json());
      setLoading(false);
    }
    load();
  }, [id]);

  const handleScore = async () => {
    setScoring(true);
    const res = await apiFetch(`/api/v1/scoring/leads/${id}`, { method: "POST" });
    if (res.ok) {
      const data = await res.json();
      setLead((prev) => prev ? { ...prev, score: data.score, tier: data.tier, annual_potential: data.annual_potential } : prev);
    }
    setScoring(false);
  };

  const handleEnrich = async () => {
    const res = await apiFetch(`/api/v1/osint/enrich/${id}`, { method: "POST" });
    if (res.ok) {
      const res2 = await apiFetch(`/api/v1/leads/${id}`);
      if (res2.ok) setLead(await res2.json());
    }
  };

  const handleDelete = async () => {
    if (!confirm("Na pewno usunąć tego leada?")) return;
    const res = await apiFetch(`/api/v1/leads/${id}`, { method: "DELETE" });
    if (res.ok) router.push("/leads");
  };

  if (loading) return <div className="text-slate-400">Ładowanie...</div>;
  if (!lead) return <div className="text-red-400">Lead nie znaleziony</div>;

  const ti = lead.tier ? tierInfo[lead.tier] : null;
  const scorePercent = lead.score ?? 0;
  const circumference = 2 * Math.PI * 54;
  const strokeDashoffset = circumference - (circumference * scorePercent) / 100;

  return (
    <div>
      {/* Header */}
      <div className="flex items-center gap-4 mb-8">
        <Link href="/leads" className="text-slate-400 hover:text-white transition-colors">&larr; Wróć</Link>
        <div className="flex-1">
          <h1 className="text-2xl font-bold text-white">{lead.name}</h1>
          <p className="text-slate-400 text-sm">NIP: {lead.nip}</p>
        </div>
        <div className="flex gap-2">
          <button onClick={handleEnrich} className="px-4 py-2 bg-purple-600 hover:bg-purple-500 text-white text-sm rounded-lg transition-colors">
            OSINT Enrich
          </button>
          <button onClick={handleScore} disabled={scoring} className="px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-blue-600/50 text-white text-sm rounded-lg transition-colors">
            {scoring ? "Scoring..." : "Przelicz score"}
          </button>
          <button onClick={handleDelete} className="px-4 py-2 bg-red-600/20 hover:bg-red-600/40 text-red-400 text-sm rounded-lg border border-red-600/30 transition-colors">
            Usuń
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Score Ring */}
        <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6 flex flex-col items-center">
          <h2 className="text-lg font-semibold text-white mb-4">Scoring</h2>
          <div className="relative w-32 h-32 mb-4">
            <svg className="w-32 h-32 -rotate-90" viewBox="0 0 120 120">
              <circle cx="60" cy="60" r="54" fill="none" stroke="#334155" strokeWidth="8" />
              <circle
                cx="60" cy="60" r="54" fill="none"
                stroke={ti ? ti.bg : "#475569"}
                strokeWidth="8"
                strokeLinecap="round"
                strokeDasharray={circumference}
                strokeDashoffset={strokeDashoffset}
                className="transition-all duration-700"
              />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className={`text-3xl font-bold ${ti?.color || "text-slate-400"}`}>
                {lead.score ?? "—"}
              </span>
              {lead.tier && (
                <span className={`text-sm font-bold ${ti?.color}`}>Tier {lead.tier}</span>
              )}
            </div>
          </div>
          {lead.annual_potential && (
            <div className="text-center">
              <p className="text-sm text-slate-400">Potencjał roczny</p>
              <p className="text-xl font-bold text-white">{(lead.annual_potential / 1000).toFixed(0)}k PLN</p>
            </div>
          )}
          {ti && (
            <div className={`mt-4 p-3 rounded-lg bg-slate-700/50 text-sm ${ti.color}`}>
              {ti.action}
            </div>
          )}
        </div>

        {/* Firmography */}
        <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6 lg:col-span-2">
          <h2 className="text-lg font-semibold text-white mb-4">Dane firmowe</h2>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <Row label="Nazwa" value={lead.name} />
            <Row label="NIP" value={lead.nip} mono />
            <Row label="Miasto" value={lead.city} />
            <Row label="Pracownicy" value={lead.employees?.toString()} />
            <Row label="Przychód" value={lead.revenue_band} />
            <Row label="Przychód (PLN)" value={lead.revenue_pln ? `${(lead.revenue_pln / 1_000_000).toFixed(1)}M PLN` : null} />
            <Row label="PKD" value={lead.pkd ? `${lead.pkd} — ${lead.pkd_desc || ""}` : null} />
            <Row label="Lata działalności" value={lead.years_active?.toString()} />
            <Row label="Status VAT" value={lead.vat_status} />
            <Row label="Strona WWW" value={lead.website} link />
            <Row label="Koszyk (PLN)" value={lead.basket_pln?.toString()} />
            <Row label="Źródła OSINT" value={lead.sources?.join(", ")} />
          </div>
        </div>
      </div>

      {/* Notes */}
      <div className="mt-6 bg-slate-800/50 border border-slate-700 rounded-xl p-6">
        <h2 className="text-lg font-semibold text-white mb-2">Notatki</h2>
        <p className="text-slate-300 text-sm whitespace-pre-wrap">{lead.notes || "Brak notatek."}</p>
      </div>
    </div>
  );
}

function Row({ label, value, mono, link }: { label: string; value: string | null | undefined; mono?: boolean; link?: boolean }) {
  return (
    <div>
      <p className="text-slate-400 text-xs mb-0.5">{label}</p>
      {link && value ? (
        <a href={value.startsWith("http") ? value : `https://${value}`} target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:text-blue-300 text-sm">
          {value}
        </a>
      ) : (
        <p className={`text-white ${mono ? "font-mono" : ""}`}>{value || "—"}</p>
      )}
    </div>
  );
}
