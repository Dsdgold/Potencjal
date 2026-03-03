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

const tierColors: Record<string, string> = {
  S: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
  A: "bg-blue-500/20 text-blue-400 border-blue-500/30",
  B: "bg-amber-500/20 text-amber-400 border-amber-500/30",
  C: "bg-slate-500/20 text-slate-400 border-slate-500/30",
};

const steps = [
  "Sprawdzam NIP w rejestrze VAT...",
  "Pobieram dane z eKRS...",
  "Pobieram dane z CEIDG...",
  "Tworzę leada...",
  "Enrich — uzupełniam dane z OSINT...",
  "Obliczam scoring potencjału...",
  "Gotowe!",
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
      // Step 1: VAT lookup to get company name
      setStep(0);
      const vatRes = await apiFetch(`/api/v1/osint/vat/${cleanNip}`);
      let companyName = "";
      let vatData = null;
      if (vatRes.ok) {
        vatData = await vatRes.json();
        companyName = vatData.name || "";
      }

      // Step 2: eKRS lookup
      setStep(1);
      const ekrsRes = await apiFetch(`/api/v1/osint/ekrs/${cleanNip}`);
      let ekrsData = null;
      if (ekrsRes.ok) {
        ekrsData = await ekrsRes.json();
        if (!companyName && ekrsData.name) companyName = ekrsData.name;
      }

      // Step 3: CEIDG lookup
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

      // Step 4: Create lead with initial data
      setStep(3);
      const createBody: Record<string, unknown> = {
        name: companyName,
        nip: cleanNip,
      };
      // Pre-fill from VAT/eKRS data
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

      // Step 5: Enrich from all OSINT sources
      setStep(4);
      await apiFetch(`/api/v1/osint/enrich/${lead.id}`, { method: "POST" });

      // Step 6: Score the lead
      setStep(5);
      await apiFetch(`/api/v1/scoring/leads/${lead.id}`, { method: "POST" });

      // Done!
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

  // Auto-start from ?nip= query param (e.g. from dashboard quick check)
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
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-white">Leady</h1>
        <button
          onClick={() => { setShowForm(!showForm); setStep(-1); setProcessing(false); setError(""); setNip(""); }}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium rounded-lg transition-colors"
        >
          {showForm ? "Anuluj" : "+ Sprawdź firmę"}
        </button>
      </div>

      {/* NIP Lookup Form */}
      {showForm && (
        <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6 mb-6">
          <h2 className="text-lg font-semibold text-white mb-2">Sprawdź potencjał firmy</h2>
          <p className="text-slate-400 text-sm mb-4">Wpisz NIP — system automatycznie pobierze dane z rejestrów (VAT, eKRS, CEIDG, GUS), utworzy leada i obliczy scoring.</p>

          {!processing ? (
            <form onSubmit={handleNipLookup} className="flex gap-3 items-end">
              <div className="flex-1 max-w-xs">
                <label className="block text-sm text-slate-300 mb-1">NIP</label>
                <input
                  value={nip}
                  onChange={(e) => setNip(e.target.value)}
                  placeholder="np. 5272700021"
                  className="w-full px-4 py-2.5 bg-slate-700/50 border border-slate-600 rounded-lg text-white text-lg font-mono tracking-wider focus:ring-2 focus:ring-blue-500 focus:outline-none"
                  maxLength={13}
                  required
                />
              </div>
              <button
                type="submit"
                className="px-6 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white font-medium rounded-lg transition-colors"
              >
                Sprawdź
              </button>
            </form>
          ) : (
            <div className="space-y-2">
              {steps.map((label, i) => (
                <div key={i} className={`flex items-center gap-3 text-sm transition-all duration-300 ${
                  i < step ? "text-emerald-400" : i === step ? "text-blue-400" : "text-slate-600"
                }`}>
                  <div className="w-5 h-5 flex items-center justify-center">
                    {i < step ? (
                      <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                      </svg>
                    ) : i === step ? (
                      <div className="w-4 h-4 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
                    ) : (
                      <div className="w-2 h-2 bg-slate-600 rounded-full" />
                    )}
                  </div>
                  {label}
                </div>
              ))}
            </div>
          )}

          {error && (
            <div className="mt-3 bg-red-500/10 border border-red-500/30 text-red-400 px-4 py-2 rounded-lg text-sm">
              {error}
            </div>
          )}
        </div>
      )}

      {/* Filters */}
      <div className="flex gap-4 mb-6">
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Szukaj po nazwie, NIP..."
          className="flex-1 max-w-sm px-4 py-2 bg-slate-800/50 border border-slate-700 rounded-lg text-white text-sm placeholder-slate-400 focus:ring-2 focus:ring-blue-500 focus:outline-none"
        />
        <select
          value={tierFilter}
          onChange={(e) => setTierFilter(e.target.value)}
          className="px-4 py-2 bg-slate-800/50 border border-slate-700 rounded-lg text-white text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
        >
          <option value="">Wszystkie tiery</option>
          <option value="S">Tier S</option>
          <option value="A">Tier A</option>
          <option value="B">Tier B</option>
          <option value="C">Tier C</option>
        </select>
      </div>

      {/* Table */}
      <div className="bg-slate-800/50 border border-slate-700 rounded-xl overflow-hidden">
        {loading ? (
          <div className="p-8 text-center text-slate-400">Ładowanie...</div>
        ) : leads.length === 0 ? (
          <div className="p-8 text-center text-slate-400">
            Brak leadów. Kliknij &quot;+ Sprawdź firmę&quot; i wpisz NIP.
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-slate-400 border-b border-slate-700 bg-slate-800/30">
                <th className="text-left py-3 px-4 font-medium">Nazwa</th>
                <th className="text-left py-3 px-4 font-medium">NIP</th>
                <th className="text-left py-3 px-4 font-medium">Miasto</th>
                <th className="text-center py-3 px-4 font-medium">Pracownicy</th>
                <th className="text-center py-3 px-4 font-medium">VAT</th>
                <th className="text-center py-3 px-4 font-medium">Score</th>
                <th className="text-center py-3 px-4 font-medium">Tier</th>
                <th className="text-right py-3 px-4 font-medium">Potencjał roczny</th>
              </tr>
            </thead>
            <tbody>
              {leads.map((lead) => (
                <tr key={lead.id} className="border-b border-slate-700/50 hover:bg-slate-700/20 transition-colors">
                  <td className="py-3 px-4">
                    <Link href={`/leads/${lead.id}`} className="text-blue-400 hover:text-blue-300 font-medium">
                      {lead.name}
                    </Link>
                  </td>
                  <td className="py-3 px-4 text-slate-300 font-mono text-xs">{lead.nip}</td>
                  <td className="py-3 px-4 text-slate-300">{lead.city || "—"}</td>
                  <td className="py-3 px-4 text-center text-slate-300">{lead.employees ?? "—"}</td>
                  <td className="py-3 px-4 text-center text-slate-300 text-xs">{lead.vat_status || "—"}</td>
                  <td className="py-3 px-4 text-center">
                    {lead.score != null ? (
                      <span className="text-white font-bold">{lead.score}</span>
                    ) : "—"}
                  </td>
                  <td className="py-3 px-4 text-center">
                    {lead.tier ? (
                      <span className={`inline-block px-2.5 py-0.5 rounded text-xs font-bold border ${tierColors[lead.tier] || ""}`}>
                        {lead.tier}
                      </span>
                    ) : "—"}
                  </td>
                  <td className="py-3 px-4 text-right text-slate-300">
                    {lead.annual_potential ? `${(lead.annual_potential / 1000).toFixed(0)}k PLN` : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
