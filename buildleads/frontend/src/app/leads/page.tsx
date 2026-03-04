"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { apiFetch } from "@/lib/api";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";

interface Lead {
  id: string;
  name: string;
  nip: string;
  city: string;
  employees: number | null;
  revenue_band: string | null;
  score: number | null;
  tier: string | null;
  annual_potential: number | null;
  vat_status: string | null;
  created_at: string;
}

const tierConfig: Record<string, { bg: string; text: string; border: string; dot: string }> = {
  S: { bg: "bg-[#22c55e]/10", text: "text-[#4ade80]", border: "border-[#22c55e]/20", dot: "bg-[#22c55e]" },
  A: { bg: "bg-[#0ea5e9]/10", text: "text-[#7dd3fc]", border: "border-[#0ea5e9]/20", dot: "bg-[#0ea5e9]" },
  B: { bg: "bg-[#f59e0b]/10", text: "text-[#fbbf24]", border: "border-[#f59e0b]/20", dot: "bg-[#f59e0b]" },
  C: { bg: "bg-[#455566]/10", text: "text-[#7b8fa0]", border: "border-[#455566]/20", dot: "bg-[#455566]" },
};

const steps = [
  "Sprawdzam NIP w rejestrze VAT...",
  "Pobieram dane z eKRS...",
  "Pobieram dane z CEIDG...",
  "Tworzę leada...",
  "Uzupełniam dane (OSINT + strona WWW + geocoding)...",
  "Obliczam scoring potencjału...",
  "Gotowe! Przekierowuję...",
];

export default function LeadsPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const autoStarted = useRef(false);
  const [leads, setLeads] = useState<Lead[]>([]);
  const [search, setSearch] = useState("");
  const [tierFilter, setTierFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);

  // NIP lookup state
  const [nip, setNip] = useState("");
  const [step, setStep] = useState(-1);
  const [error, setError] = useState("");
  const [processing, setProcessing] = useState(false);

  const load = async () => {
    const params = new URLSearchParams();
    if (search) params.set("q", search);
    if (tierFilter) params.set("tier", tierFilter);
    params.set("limit", "100");
    const res = await apiFetch(`/api/v1/leads?${params}`);
    if (res.ok) {
      const data = await res.json();
      setLeads(data.items || data);
    }
    setLoading(false);
  };

  useEffect(() => { load(); }, [search, tierFilter]);

  const runNipLookup = useCallback(async (inputNip: string) => {
    const cleanNip = inputNip.replace(/[\s-]/g, "");
    if (!/^\d{10}$/.test(cleanNip)) {
      setError("NIP musi mieć 10 cyfr");
      return;
    }

    setError("");
    setProcessing(true);
    setStep(0);

    try {
      setStep(0);
      const vatRes = await apiFetch(`/api/v1/osint/vat/${cleanNip}`);
      let companyName = "";
      let vatData = null;
      if (vatRes.ok) {
        vatData = await vatRes.json();
        companyName = vatData.name || "";
      }

      setStep(1);
      const ekrsRes = await apiFetch(`/api/v1/osint/ekrs/${cleanNip}`);
      let ekrsData = null;
      if (ekrsRes.ok) {
        ekrsData = await ekrsRes.json();
        if (!companyName && ekrsData.name) companyName = ekrsData.name;
      }

      setStep(2);
      const ceidgRes = await apiFetch(`/api/v1/osint/ceidg/${cleanNip}`);
      let ceidgData = null;
      if (ceidgRes.ok) {
        ceidgData = await ceidgRes.json();
        if (!companyName && ceidgData.name) companyName = ceidgData.name;
      }

      if (!companyName) {
        companyName = `Firma NIP ${cleanNip}`;
      }

      setStep(3);
      const createBody: Record<string, unknown> = {
        name: companyName,
        nip: cleanNip,
      };
      if (vatData?.city) createBody.city = vatData.city;
      if (vatData?.vat_status) createBody.vat_status = vatData.vat_status;
      if (ekrsData?.pkd) createBody.pkd = ekrsData.pkd;
      if (ekrsData?.years_active) createBody.years_active = ekrsData.years_active;
      if (ceidgData?.website) createBody.website = ceidgData.website;

      const createRes = await apiFetch("/api/v1/leads", {
        method: "POST",
        body: JSON.stringify(createBody),
      });

      if (!createRes.ok) {
        const err = await createRes.json().catch(() => null);
        throw new Error(err?.detail || "Nie udało się utworzyć leada");
      }

      const lead = await createRes.json();

      setStep(4);
      await apiFetch(`/api/v1/osint/enrich/${lead.id}`, { method: "POST" });

      setStep(5);
      await apiFetch(`/api/v1/scoring/leads/${lead.id}`, { method: "POST" });

      setStep(6);
      setTimeout(() => {
        router.push(`/leads/${lead.id}`);
      }, 600);

    } catch (err) {
      setError(err instanceof Error ? err.message : "Wystąpił błąd");
      setProcessing(false);
      setStep(-1);
    }
  }, [router]);

  const handleNipLookup = async (e: React.FormEvent) => {
    e.preventDefault();
    runNipLookup(nip);
  };

  useEffect(() => {
    const qnip = searchParams.get("nip");
    if (qnip && !autoStarted.current) {
      autoStarted.current = true;
      setNip(qnip);
      setShowForm(true);
      runNipLookup(qnip);
    }
  }, [searchParams, runNipLookup]);

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-[#e8edf2]">Leady</h1>
          <p className="text-[#455566] text-xs mt-0.5">Baza firm i ich potencjal sprzedazowy</p>
        </div>
        <button
          onClick={() => { setShowForm(!showForm); setStep(-1); setProcessing(false); setError(""); setNip(""); }}
          className="px-5 py-2.5 bg-gradient-to-r from-[#0ea5e9] to-[#38bdf8] hover:from-[#38bdf8] hover:to-[#7dd3fc] text-white text-sm font-semibold rounded-xl transition-all shadow-lg shadow-[#0ea5e9]/20 hover:shadow-[#0ea5e9]/30 hover:-translate-y-0.5 active:translate-y-0"
        >
          {showForm ? "Anuluj" : "+ Sprawdz firme"}
        </button>
      </div>

      {/* NIP Lookup Form */}
      {showForm && (
        <div className="bg-[#0f171e] border border-[rgba(14,165,233,0.08)] rounded-2xl p-6 mb-6 animate-slide-up">
          <h2 className="text-base font-semibold text-[#e8edf2] mb-2">Sprawdz potencjal firmy</h2>
          <p className="text-[#455566] text-sm mb-4">Wpisz NIP — system automatycznie pobierze dane z rejestrow (VAT, eKRS, CEIDG, GUS), utworzy leada i obliczy scoring.</p>

          {!processing ? (
            <form onSubmit={handleNipLookup} className="flex gap-3 items-end">
              <div className="flex-1 max-w-xs">
                <label className="block text-[10px] text-[#455566] mb-1.5 uppercase tracking-[0.15em] font-semibold">NIP</label>
                <input
                  value={nip}
                  onChange={(e) => setNip(e.target.value)}
                  placeholder="np. 5272700021"
                  className="w-full px-4 py-2.5 bg-[#020709] border border-[rgba(14,165,233,0.08)] rounded-xl text-[#e8edf2] text-lg font-mono tracking-wider placeholder-[#455566] focus:ring-2 focus:ring-[#0ea5e9]/30 focus:border-[#0ea5e9]/30 focus:outline-none transition-all"
                  maxLength={13}
                  required
                />
              </div>
              <button
                type="submit"
                className="px-6 py-2.5 bg-[#22c55e] hover:bg-[#4ade80] text-white font-semibold rounded-xl transition-all shadow-lg shadow-[#22c55e]/20"
              >
                Sprawdz
              </button>
            </form>
          ) : (
            <div className="space-y-2.5">
              {steps.map((label, i) => (
                <div key={i} className={`flex items-center gap-3 text-sm transition-all duration-300 ${
                  i < step ? "text-[#22c55e]" : i === step ? "text-[#0ea5e9]" : "text-[#1e2d3a]"
                }`}>
                  <div className="w-5 h-5 flex items-center justify-center">
                    {i < step ? (
                      <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                      </svg>
                    ) : i === step ? (
                      <div className="w-4 h-4 border-2 border-[#0ea5e9] border-t-transparent rounded-full animate-spin" />
                    ) : (
                      <div className="w-2 h-2 bg-[#1e2d3a] rounded-full" />
                    )}
                  </div>
                  {label}
                </div>
              ))}
            </div>
          )}

          {error && (
            <div className="mt-3 bg-[#ef4444]/8 border border-[#ef4444]/20 text-[#ef4444] px-4 py-2.5 rounded-xl text-sm">
              {error}
            </div>
          )}
        </div>
      )}

      {/* Filters */}
      <div className="flex gap-3 mb-6">
        <div className="relative flex-1 max-w-sm">
          <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#455566]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Szukaj po nazwie, NIP..."
            className="w-full pl-10 pr-4 py-2.5 bg-[#0f171e] border border-[rgba(14,165,233,0.08)] rounded-xl text-[#e8edf2] text-sm placeholder-[#455566] focus:ring-2 focus:ring-[#0ea5e9]/30 focus:outline-none transition-all"
          />
        </div>
        <select
          value={tierFilter}
          onChange={(e) => setTierFilter(e.target.value)}
          className="px-4 py-2.5 bg-[#0f171e] border border-[rgba(14,165,233,0.08)] rounded-xl text-[#e8edf2] text-sm focus:ring-2 focus:ring-[#0ea5e9]/30 focus:outline-none transition-all"
        >
          <option value="">Wszystkie tiery</option>
          <option value="S">Tier S</option>
          <option value="A">Tier A</option>
          <option value="B">Tier B</option>
          <option value="C">Tier C</option>
        </select>
      </div>

      {/* Table */}
      <div className="bg-[#0f171e] border border-[rgba(14,165,233,0.08)] rounded-2xl overflow-hidden">
        {loading ? (
          <div className="p-12 text-center">
            <div className="w-8 h-8 border-2 border-[#0ea5e9] border-t-transparent rounded-full animate-spin mx-auto mb-3" />
            <p className="text-[#455566] text-sm">Ladowanie...</p>
          </div>
        ) : leads.length === 0 ? (
          <div className="p-12 text-center">
            <div className="w-12 h-12 rounded-2xl bg-[#0ea5e9]/10 flex items-center justify-center mx-auto mb-3">
              <svg className="w-6 h-6 text-[#0ea5e9]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M18 18.72a9.094 9.094 0 003.741-.479 3 3 0 00-4.682-2.72m.94 3.198l.001.031c0 .225-.012.447-.037.666A11.944 11.944 0 0112 21c-2.17 0-4.207-.576-5.963-1.584A6.062 6.062 0 016 18.719m12 0a5.971 5.971 0 00-.941-3.197m0 0A5.995 5.995 0 0012 12.75a5.995 5.995 0 00-5.058 2.772m0 0a3 3 0 00-4.681 2.72 8.986 8.986 0 003.74.477m.94-3.197a5.971 5.971 0 00-.94 3.197M15 6.75a3 3 0 11-6 0 3 3 0 016 0zm6 3a2.25 2.25 0 11-4.5 0 2.25 2.25 0 014.5 0zm-13.5 0a2.25 2.25 0 11-4.5 0 2.25 2.25 0 014.5 0z" />
              </svg>
            </div>
            <p className="text-[#7b8fa0] text-sm">Brak leadow. Kliknij &quot;+ Sprawdz firme&quot; i wpisz NIP.</p>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-[#455566] border-b border-[rgba(14,165,233,0.06)]">
                <th className="text-left py-3.5 px-4 font-semibold text-[10px] uppercase tracking-[0.15em]">Nazwa</th>
                <th className="text-left py-3.5 px-4 font-semibold text-[10px] uppercase tracking-[0.15em]">NIP</th>
                <th className="text-left py-3.5 px-4 font-semibold text-[10px] uppercase tracking-[0.15em]">Miasto</th>
                <th className="text-center py-3.5 px-4 font-semibold text-[10px] uppercase tracking-[0.15em]">Pracownicy</th>
                <th className="text-center py-3.5 px-4 font-semibold text-[10px] uppercase tracking-[0.15em]">VAT</th>
                <th className="text-center py-3.5 px-4 font-semibold text-[10px] uppercase tracking-[0.15em]">Score</th>
                <th className="text-center py-3.5 px-4 font-semibold text-[10px] uppercase tracking-[0.15em]">Tier</th>
                <th className="text-right py-3.5 px-4 font-semibold text-[10px] uppercase tracking-[0.15em]">Potencjal roczny</th>
              </tr>
            </thead>
            <tbody>
              {leads.map((lead) => {
                const tc = tierConfig[lead.tier || ""] || tierConfig.C;
                return (
                  <tr key={lead.id} className="border-b border-[rgba(14,165,233,0.04)] hover:bg-[#162028] transition-colors group">
                    <td className="py-3.5 px-4">
                      <Link href={`/leads/${lead.id}`} className="text-[#7dd3fc] hover:text-[#bae6fd] font-medium transition-colors">
                        {lead.name}
                      </Link>
                    </td>
                    <td className="py-3.5 px-4 text-[#455566] font-mono text-xs">{lead.nip}</td>
                    <td className="py-3.5 px-4 text-[#7b8fa0]">{lead.city || "—"}</td>
                    <td className="py-3.5 px-4 text-center text-[#7b8fa0]">{lead.employees ?? "—"}</td>
                    <td className="py-3.5 px-4 text-center">
                      {lead.vat_status ? (
                        <span className={`text-xs ${lead.vat_status === "Czynny" ? "text-[#22c55e]" : "text-[#455566]"}`}>
                          {lead.vat_status}
                        </span>
                      ) : "—"}
                    </td>
                    <td className="py-3.5 px-4 text-center">
                      {lead.score != null ? (
                        <span className="text-[#e8edf2] font-bold">{lead.score}</span>
                      ) : "—"}
                    </td>
                    <td className="py-3.5 px-4 text-center">
                      {lead.tier ? (
                        <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-lg text-xs font-bold border ${tc.bg} ${tc.text} ${tc.border}`}>
                          <span className={`w-1.5 h-1.5 rounded-full ${tc.dot}`} />
                          {lead.tier}
                        </span>
                      ) : "—"}
                    </td>
                    <td className="py-3.5 px-4 text-right text-[#7b8fa0]">
                      {lead.annual_potential ? `${(lead.annual_potential / 1000).toFixed(0)}k PLN` : "—"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
