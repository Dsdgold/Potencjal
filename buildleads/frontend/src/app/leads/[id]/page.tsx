"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api";
import Link from "next/link";
import dynamic from "next/dynamic";

const LeadMap = dynamic(() => import("@/components/lead-map"), { ssr: false });

interface Lead {
  id: string;
  name: string;
  nip: string;
  city: string;
  voivodeship: string | null;
  street: string | null;
  postal_code: string | null;
  regon: string | null;
  krs: string | null;
  legal_form: string | null;
  latitude: number | null;
  longitude: number | null;
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
  osint_raw: Record<string, unknown> | null;
  status: string;
  contact_company: string | null;
  contact_person: string | null;
  contact_phone: string | null;
  contact_email: string | null;
  category: string | null;
  title: string | null;
  description: string | null;
  ai_summary: string | null;
  board_members: Array<{name: string; function: string}> | null;
  social_media: Record<string, string> | null;
  created_at: string;
  updated_at: string;
}

interface BreakdownItem {
  factor: string;
  label: string;
  raw_score: number;
  weight: number;
  weighted_score: number;
}

interface ScoringResult {
  score: number;
  tier: string;
  annual_potential: number;
  revenue_band: string;
  categories: string[];
  recommended_actions: string[];
  breakdown: BreakdownItem[];
}

interface HistoryEntry {
  id: string;
  score: number;
  tier: string;
  annual_potential: number;
  scored_at: string;
}

const tierInfo: Record<string, { color: string; bg: string; border: string; label: string; action: string }> = {
  S: { color: "text-emerald-400", bg: "bg-emerald-500", border: "border-emerald-500/30", label: "PREMIUM", action: "Priorytetowy kontakt osobisty — zadzwoń dziś!" },
  A: { color: "text-blue-400", bg: "bg-blue-500", border: "border-blue-500/30", label: "WYSOKI", action: "Oferta rabatu ilościowego, dostawa 24–48h" },
  B: { color: "text-amber-400", bg: "bg-amber-500", border: "border-amber-500/30", label: "ŚREDNI", action: "Kampania remarketingowa, follow-up 7 dni" },
  C: { color: "text-slate-400", bg: "bg-slate-500", border: "border-slate-500/30", label: "NISKI", action: "Monitoruj, follow-up 30 dni" },
};

const revenueBandLabels: Record<string, string> = {
  micro: "< 2M PLN (mikro)",
  small: "2–10M PLN (mała)",
  medium: "10–50M PLN (średnia)",
  large: "> 50M PLN (duża)",
};

const sourceLabels: Record<string, string> = {
  vat_whitelist: "Biała Lista VAT (MF)",
  ekrs: "eKRS (Min. Sprawiedliwości)",
  ceidg: "CEIDG (biznes.gov.pl)",
  gus: "GUS REGON (stat.gov.pl)",
};

export default function LeadDetailPage() {
  const { id } = useParams();
  const router = useRouter();
  const [lead, setLead] = useState<Lead | null>(null);
  const [loading, setLoading] = useState(true);
  const [scoring, setScoring] = useState(false);
  const [enriching, setEnriching] = useState(false);
  const [scoringResult, setScoringResult] = useState<ScoringResult | null>(null);
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [showOsintRaw, setShowOsintRaw] = useState(false);
  const [editingNotes, setEditingNotes] = useState(false);
  const [notesValue, setNotesValue] = useState("");

  useEffect(() => {
    async function load() {
      const [leadRes, histRes] = await Promise.all([
        apiFetch(`/api/v1/leads/${id}`),
        apiFetch(`/api/v1/scoring/leads/${id}/history`),
      ]);
      if (leadRes.ok) {
        const data = await leadRes.json();
        setLead(data);
        setNotesValue(data.notes || "");
      }
      if (histRes.ok) setHistory(await histRes.json());
      setLoading(false);

      // Auto-trigger scoring on load to get breakdown
      try {
        const scoreRes = await apiFetch(`/api/v1/scoring/leads/${id}`, { method: "POST" });
        if (scoreRes.ok) {
          const scoreData: ScoringResult = await scoreRes.json();
          setScoringResult(scoreData);
          setLead((prev) => prev ? { ...prev, score: scoreData.score, tier: scoreData.tier, annual_potential: scoreData.annual_potential, revenue_band: scoreData.revenue_band } : prev);
          // Refresh history after auto-score
          const hRes = await apiFetch(`/api/v1/scoring/leads/${id}/history`);
          if (hRes.ok) setHistory(await hRes.json());
        }
      } catch {
        // Scoring auto-trigger failed silently
      }
    }
    load();
  }, [id]);

  const handleScore = async () => {
    setScoring(true);
    const res = await apiFetch(`/api/v1/scoring/leads/${id}`, { method: "POST" });
    if (res.ok) {
      const data: ScoringResult = await res.json();
      setScoringResult(data);
      setLead((prev) => prev ? { ...prev, score: data.score, tier: data.tier, annual_potential: data.annual_potential, revenue_band: data.revenue_band } : prev);
      // Refresh history
      const hRes = await apiFetch(`/api/v1/scoring/leads/${id}/history`);
      if (hRes.ok) setHistory(await hRes.json());
    }
    setScoring(false);
  };

  const handleEnrich = async () => {
    setEnriching(true);
    const res = await apiFetch(`/api/v1/osint/enrich/${id}`, { method: "POST" });
    if (res.ok) {
      const res2 = await apiFetch(`/api/v1/leads/${id}`);
      if (res2.ok) {
        const data = await res2.json();
        setLead(data);
        setNotesValue(data.notes || "");
      }
    }
    setEnriching(false);
  };

  const handleEnrichAndScore = async () => {
    setEnriching(true);
    setScoring(true);
    // Enrich
    await apiFetch(`/api/v1/osint/enrich/${id}`, { method: "POST" });
    // Re-read lead
    const res2 = await apiFetch(`/api/v1/leads/${id}`);
    if (res2.ok) {
      const data = await res2.json();
      setLead(data);
      setNotesValue(data.notes || "");
    }
    setEnriching(false);
    // Score
    const scoreRes = await apiFetch(`/api/v1/scoring/leads/${id}`, { method: "POST" });
    if (scoreRes.ok) {
      const data: ScoringResult = await scoreRes.json();
      setScoringResult(data);
      setLead((prev) => prev ? { ...prev, score: data.score, tier: data.tier, annual_potential: data.annual_potential, revenue_band: data.revenue_band } : prev);
      const hRes = await apiFetch(`/api/v1/scoring/leads/${id}/history`);
      if (hRes.ok) setHistory(await hRes.json());
    }
    setScoring(false);
  };

  const handleDelete = async () => {
    if (!confirm("Na pewno usunąć tego leada?")) return;
    const res = await apiFetch(`/api/v1/leads/${id}`, { method: "DELETE" });
    if (res.ok) router.push("/leads");
  };

  const saveNotes = async () => {
    const res = await apiFetch(`/api/v1/leads/${id}`, {
      method: "PUT",
      body: JSON.stringify({ notes: notesValue }),
    });
    if (res.ok) {
      setLead((prev) => prev ? { ...prev, notes: notesValue } : prev);
      setEditingNotes(false);
    }
  };

  if (loading) return <div className="text-slate-400 p-8">Ładowanie danych firmy...</div>;
  if (!lead) return <div className="text-red-400 p-8">Lead nie znaleziony</div>;

  const ti = lead.tier ? tierInfo[lead.tier] : null;
  const scorePercent = lead.score ?? 0;
  const circumference = 2 * Math.PI * 54;
  const strokeDashoffset = circumference - (circumference * scorePercent) / 100;

  // Extract structured data from OSINT raw
  const vatRaw = lead.osint_raw?.vat_whitelist as Record<string, unknown> | undefined;
  const vatSubject = vatRaw?.result
    ? (vatRaw.result as Record<string, unknown>)?.subject as Record<string, unknown> | undefined
    : undefined;
  const ekrsRaw = lead.osint_raw?.ekrs as Record<string, unknown> | undefined;
  const ekrsParsed = ekrsRaw?._parsed as Record<string, unknown> | undefined;
  const gusRaw = lead.osint_raw?.gus as Record<string, unknown> | undefined;
  const gusParsed = gusRaw?._parsed as Record<string, unknown> | undefined;

  // Board of directors — eKRS may return anonymized names (RODO: "J**** K****")
  // In that case, prefer VAT White List representatives which have full names
  const ekrsBoard = (ekrsParsed?.board as Array<{name: string; function: string}>) || [];
  const boardOrganName = ekrsParsed?.board_organ_name as string || "Zarząd";
  const ekrsBoardMasked = ekrsBoard.length > 0 && ekrsBoard.some(m => (m.name || "").includes("*"));
  const supervisory = (ekrsParsed?.supervisory as Array<{name: string; function: string}>) || [];
  // Shareholders
  const shareholders = (ekrsParsed?.shareholders as Array<{name: string; shares: string}>) || [];
  const shareCapital = ekrsParsed?.capital as string | null;
  // PKD codes
  const pkdAll = (ekrsParsed?.pkd_all as Array<{code: string; desc: string}>) || [];
  // Legal form
  const legalForm = ekrsParsed?.legal_form as string | null;
  const ekrsAddress = ekrsParsed?.full_address as Record<string, string> | undefined;
  // VAT representatives (always have full, non-anonymized names)
  const vatRepresentatives = (vatSubject?.representatives as Array<{firstName?: string; lastName?: string; companyName?: string}>) || [];
  const vatPartners = (vatSubject?.partners as Array<{firstName?: string; lastName?: string; companyName?: string}>) || [];
  // Build effective board: prefer lead.board_members (backend already demasked), then VAT reps, then eKRS
  const savedBoard = lead.board_members || [];
  const savedBoardMasked = savedBoard.length > 0 && savedBoard.some(m => (m.name || "").includes("*"));
  const vatBoardMembers = vatRepresentatives
    .map(r => ({ name: (r.companyName || `${r.firstName || ""} ${r.lastName || ""}`.trim()) || "—", function: "Reprezentant" }))
    .filter(m => m.name !== "—" && !m.name.includes("*"));
  const vatPartnerMembers = vatPartners
    .map(p => ({ name: (p.companyName || `${p.firstName || ""} ${p.lastName || ""}`.trim()) || "—", function: "Wspólnik" }))
    .filter(m => m.name !== "—" && !m.name.includes("*"));
  // Choose the best source of board members
  const board = (savedBoard.length > 0 && !savedBoardMasked)
    ? savedBoard
    : (vatBoardMembers.length > 0 ? [...vatBoardMembers, ...vatPartnerMembers] : (!ekrsBoardMasked ? ekrsBoard : []));
  // Bank accounts
  const bankAccounts = Array.isArray(vatSubject?.accountNumbers) ? vatSubject.accountNumbers as string[] : [];
  // Addresses
  const residenceAddress = vatSubject?.residenceAddress ? String(vatSubject.residenceAddress) : null;
  const workingAddress = vatSubject?.workingAddress ? String(vatSubject.workingAddress) : null;
  // Registration
  const regDate = vatSubject?.registrationLegalDate ? String(vatSubject.registrationLegalDate) : ekrsParsed?.registration_date as string | null;
  // Identifiers
  const regon = vatSubject?.regon ? String(vatSubject.regon) : gusParsed?.regon ? String(gusParsed.regon) : null;
  const krsNum = vatSubject?.krs ? String(vatSubject.krs) : gusParsed?.krs ? String(gusParsed.krs) : (ekrsParsed?.nip ? null : null);
  const gusLegalForm = gusParsed?.legal_form ? String(gusParsed.legal_form) : null;
  const gusPkd = gusParsed?.pkd ? String(gusParsed.pkd) : null;
  const gusPkdDesc = gusParsed?.pkd_desc ? String(gusParsed.pkd_desc) : null;
  const gusVoivodeship = gusParsed?.voivodeship ? String(gusParsed.voivodeship) : null;
  const gusStreet = gusParsed?.street ? String(gusParsed.street) : null;
  const gusBuilding = gusParsed?.building ? String(gusParsed.building) : null;
  const gusPostalCode = gusParsed?.postal_code ? String(gusParsed.postal_code) : null;

  return (
    <div className="max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-start gap-4 mb-6">
        <Link href="/leads" className="mt-2 text-slate-400 hover:text-white transition-colors text-lg">&larr;</Link>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3 mb-1">
            <h1 className="text-2xl font-bold text-white truncate">{lead.name}</h1>
            {lead.tier && (
              <span className={`inline-block px-3 py-0.5 rounded text-xs font-bold border ${ti?.bg}/20 ${ti?.color} ${ti?.border}`}>
                Tier {lead.tier} — {ti?.label}
              </span>
            )}
            <span className={`inline-block px-2 py-0.5 rounded text-xs border ${lead.vat_status === "Czynny VAT" ? "bg-emerald-500/20 text-emerald-400 border-emerald-500/30" : "bg-red-500/20 text-red-400 border-red-500/30"}`}>
              {lead.vat_status || "VAT nieznany"}
            </span>
          </div>
          <div className="flex items-center gap-4 text-sm text-slate-400">
            <span className="font-mono">NIP: {lead.nip}</span>
            {lead.city && <span>{lead.city}{lead.voivodeship ? `, woj. ${lead.voivodeship}` : ""}</span>}
            {lead.pkd && <span>PKD: {lead.pkd}</span>}
            {lead.website && (
              <a href={lead.website.startsWith("http") ? lead.website : `https://${lead.website}`} target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:text-blue-300">
                {lead.website}
              </a>
            )}
          </div>
        </div>
        <div className="flex gap-2 flex-shrink-0">
          <button onClick={handleEnrichAndScore} disabled={enriching || scoring} className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:bg-emerald-600/50 text-white text-sm rounded-lg transition-colors font-medium">
            {enriching ? "Pobieranie..." : scoring ? "Scoring..." : "Odśwież dane + Score"}
          </button>
          <button onClick={handleDelete} className="px-3 py-2 bg-red-600/20 hover:bg-red-600/40 text-red-400 text-sm rounded-lg border border-red-600/30 transition-colors">
            Usuń
          </button>
        </div>
      </div>

      {/* Row 1: Score + Tier Action + Potential */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4 mb-4">
        {/* Score Ring */}
        <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6 flex flex-col items-center">
          <div className="relative w-32 h-32 mb-3">
            <svg className="w-32 h-32 -rotate-90" viewBox="0 0 120 120">
              <circle cx="60" cy="60" r="54" fill="none" stroke="#334155" strokeWidth="8" />
              <circle
                cx="60" cy="60" r="54" fill="none"
                stroke={ti ? `var(--tier-stroke)` : "#475569"}
                strokeWidth="8" strokeLinecap="round"
                strokeDasharray={circumference} strokeDashoffset={strokeDashoffset}
                className="transition-all duration-700"
                style={{ "--tier-stroke": ti ? (lead.tier === "S" ? "#10b981" : lead.tier === "A" ? "#3b82f6" : lead.tier === "B" ? "#f59e0b" : "#64748b") : "#475569" } as React.CSSProperties}
              />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className={`text-3xl font-bold ${ti?.color || "text-slate-400"}`}>{lead.score ?? "—"}</span>
              <span className="text-xs text-slate-500">/ 100</span>
            </div>
          </div>
          {lead.tier && <span className={`text-sm font-bold ${ti?.color}`}>Tier {lead.tier}</span>}
        </div>

        {/* Recommended action */}
        <div className={`lg:col-span-2 bg-slate-800/50 border rounded-xl p-6 ${ti?.border || "border-slate-700"}`}>
          <h3 className="text-sm font-semibold text-slate-400 mb-2 uppercase tracking-wider">Rekomendowana akcja</h3>
          {ti ? (
            <p className={`text-lg font-medium ${ti.color} mb-3`}>{ti.action}</p>
          ) : (
            <p className="text-slate-500">Przelicz scoring aby otrzymać rekomendację</p>
          )}
          {scoringResult?.recommended_actions && scoringResult.recommended_actions.length > 0 && (
            <ul className="space-y-1.5 mt-2">
              {scoringResult.recommended_actions.map((a, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-slate-300">
                  <span className="text-blue-400 mt-0.5">&#x2022;</span> {a}
                </li>
              ))}
            </ul>
          )}
          {scoringResult?.categories && scoringResult.categories.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-1.5">
              {scoringResult.categories.map((c, i) => (
                <span key={i} className="px-2 py-0.5 bg-blue-500/10 text-blue-400 border border-blue-500/20 rounded text-xs">
                  {c}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Potential */}
        <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
          <h3 className="text-sm font-semibold text-slate-400 mb-2 uppercase tracking-wider">Potencjał roczny</h3>
          <p className="text-3xl font-bold text-white">
            {lead.annual_potential ? `${(lead.annual_potential / 1000).toFixed(0)}k` : "—"}
            <span className="text-base font-normal text-slate-400 ml-1">PLN</span>
          </p>
          {lead.revenue_band && (
            <p className="text-sm text-slate-400 mt-2">
              Przychód: {revenueBandLabels[lead.revenue_band] || lead.revenue_band}
            </p>
          )}
          <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
            <div className="bg-slate-700/30 rounded p-2 text-center">
              <p className="text-slate-400">Status</p>
              <p className="text-white font-medium capitalize">{lead.status}</p>
            </div>
            <div className="bg-slate-700/30 rounded p-2 text-center">
              <p className="text-slate-400">Źródło</p>
              <p className="text-white font-medium">{lead.sources?.length || 0} rejestrów</p>
            </div>
          </div>
        </div>
      </div>

      {/* Row 2: Scoring Breakdown + Firmography */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
        {/* Scoring Breakdown */}
        <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-white">Scoring — rozkład czynników</h2>
            <button onClick={handleScore} disabled={scoring} className="text-xs text-blue-400 hover:text-blue-300">
              {scoring ? "Liczenie..." : "Przelicz"}
            </button>
          </div>
          {scoringResult?.breakdown ? (
            <div className="space-y-3">
              {scoringResult.breakdown.map((b) => (
                <div key={b.factor}>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-slate-300">{b.label}</span>
                    <span className="text-slate-400">
                      <span className="text-white font-medium">{b.raw_score}</span>/100 &times; {(b.weight * 100).toFixed(0)}% = <span className="text-white font-medium">{b.weighted_score.toFixed(1)}</span>
                    </span>
                  </div>
                  <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-500 ${b.raw_score >= 70 ? "bg-emerald-500" : b.raw_score >= 50 ? "bg-blue-500" : b.raw_score >= 30 ? "bg-amber-500" : "bg-red-500"}`}
                      style={{ width: `${b.raw_score}%` }}
                    />
                  </div>
                </div>
              ))}
              <div className="border-t border-slate-700 pt-2 mt-3 flex justify-between text-sm">
                <span className="text-slate-400 font-medium">Suma ważona</span>
                <span className="text-white font-bold">{lead.score ?? "—"} / 100</span>
              </div>
            </div>
          ) : (
            <div className="text-center py-8">
              <p className="text-slate-500 mb-3">Kliknij &quot;Przelicz&quot; aby zobaczyć rozkład scoringu</p>
              <button onClick={handleScore} disabled={scoring} className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm rounded-lg transition-colors">
                Przelicz scoring
              </button>
            </div>
          )}
        </div>

        {/* Full Firmography */}
        <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
          <h2 className="text-lg font-semibold text-white mb-4">Dane firmowe</h2>
          <div className="grid grid-cols-2 gap-x-6 gap-y-3 text-sm">
            <FirmoRow label="Pełna nazwa" value={lead.name} />
            <FirmoRow label="NIP" value={lead.nip} mono />
            <FirmoRow label="REGON" value={lead.regon || regon} mono />
            <FirmoRow label="KRS" value={lead.krs || krsNum} mono />
            <FirmoRow label="Forma prawna" value={lead.legal_form || legalForm || gusLegalForm} />
            <FirmoRow label="Adres" value={lead.street ? [lead.street, lead.postal_code, lead.city].filter(Boolean).join(", ") : lead.city} />
            <FirmoRow label="Województwo" value={lead.voivodeship || gusVoivodeship} />
            <FirmoRow label="PKD (główny)" value={lead.pkd ? `${lead.pkd}${lead.pkd_desc ? ` — ${lead.pkd_desc}` : ""}` : null} />
            <FirmoRow label="Lata działalności" value={lead.years_active != null ? `${lead.years_active.toFixed(1)} lat` : null} />
            <FirmoRow label="Status VAT" value={lead.vat_status} highlight={lead.vat_status === "Czynny VAT" ? "green" : lead.vat_status === "Zwolniony" ? "yellow" : "red"} />
            <FirmoRow label="Strona WWW" value={lead.website} link />
            <FirmoRow label="Pracownicy" value={lead.employees != null ? `${lead.employees} os.` : null} />
            <FirmoRow label="Przychód roczny" value={lead.revenue_pln ? `${(lead.revenue_pln / 1_000_000).toFixed(1)}M PLN` : null} />
            <FirmoRow label="Pasmo przychodów" value={lead.revenue_band ? revenueBandLabels[lead.revenue_band] || lead.revenue_band : null} />
            <FirmoRow label="Kategoria" value={lead.category} />
            <FirmoRow label="Dodano" value={new Date(lead.created_at).toLocaleDateString("pl-PL", { year: "numeric", month: "long", day: "numeric" })} />
          </div>
        </div>
      </div>

      {/* Row 2.5: Registry IDs + Addresses + Board/Representatives */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-4">
        {/* Registry Identifiers + Addresses */}
        <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
          <h2 className="text-lg font-semibold text-white mb-4">Dane rejestrowe</h2>
          <div className="space-y-3 text-sm">
            <FirmoRow label="NIP" value={lead.nip} mono />
            <FirmoRow label="REGON" value={regon} mono />
            <FirmoRow label="KRS" value={krsNum} mono />
            <FirmoRow label="Forma prawna" value={legalForm || gusLegalForm} />
            <FirmoRow label="Data rejestracji" value={regDate} />
            {lead.years_active != null && <FirmoRow label="Lata działalności" value={`${lead.years_active.toFixed(1)} lat`} />}
            {gusVoivodeship && <FirmoRow label="Województwo (GUS)" value={gusVoivodeship} />}
            {gusPkd && !lead.pkd && <FirmoRow label="PKD (GUS)" value={`${gusPkd}${gusPkdDesc ? ` — ${gusPkdDesc}` : ""}`} />}
          </div>
          {(residenceAddress || workingAddress) && (
            <div className="mt-4 pt-3 border-t border-slate-700">
              <p className="text-xs text-slate-500 mb-2 uppercase tracking-wider">Adresy</p>
              {residenceAddress && (
                <div className="mb-2">
                  <p className="text-xs text-slate-500">Adres siedziby</p>
                  <p className="text-sm text-slate-300">{residenceAddress}</p>
                </div>
              )}
              {workingAddress && workingAddress !== residenceAddress && (
                <div>
                  <p className="text-xs text-slate-500">Adres prowadzenia działalności</p>
                  <p className="text-sm text-slate-300">{workingAddress}</p>
                </div>
              )}
            </div>
          )}
          {ekrsAddress && Object.keys(ekrsAddress).length > 0 && !residenceAddress && (
            <div className="mt-4 pt-3 border-t border-slate-700">
              <p className="text-xs text-slate-500 mb-2 uppercase tracking-wider">Adres z KRS</p>
              <p className="text-sm text-slate-300">
                {[ekrsAddress.ulica, ekrsAddress.nrDomu, ekrsAddress.nrLokalu].filter(Boolean).join(" ")}
                {ekrsAddress.kodPocztowy ? `, ${ekrsAddress.kodPocztowy}` : ""}
                {ekrsAddress.miejscowosc ? ` ${ekrsAddress.miejscowosc}` : ""}
              </p>
            </div>
          )}
          {gusStreet && !residenceAddress && !ekrsAddress && (
            <div className="mt-4 pt-3 border-t border-slate-700">
              <p className="text-xs text-slate-500 mb-2 uppercase tracking-wider">Adres z GUS</p>
              <p className="text-sm text-slate-300">
                {[gusStreet, gusBuilding].filter(Boolean).join(" ")}
                {gusPostalCode ? `, ${gusPostalCode}` : ""}
                {lead.city ? ` ${lead.city}` : ""}
              </p>
            </div>
          )}
        </div>

        {/* Board of Directors + Representatives */}
        <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
          <h2 className="text-lg font-semibold text-white mb-4">Zarząd i Reprezentacja</h2>
          {board.length > 0 ? (
            <div>
              <p className="text-xs text-slate-500 mb-2 uppercase tracking-wider">{boardOrganName}</p>
              <div className="space-y-2">
                {board.map((m, i) => (
                  <div key={i} className="flex items-center justify-between p-2 bg-slate-700/30 rounded-lg">
                    <span className="text-sm text-white font-medium">{m.name}</span>
                    <span className="text-xs text-slate-400">{m.function}</span>
                  </div>
                ))}
              </div>
            </div>
          ) : vatRepresentatives.length > 0 ? (
            <div>
              <p className="text-xs text-slate-500 mb-2 uppercase tracking-wider">Reprezentanci (Biała Lista VAT)</p>
              <div className="space-y-2">
                {vatRepresentatives.map((r, i) => (
                  <div key={i} className="p-2 bg-slate-700/30 rounded-lg text-sm text-white">
                    {r.companyName || `${r.firstName || ""} ${r.lastName || ""}`.trim() || "—"}
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <p className="text-slate-500 text-sm">Brak danych o zarządzie. Kliknij &quot;Odśwież dane&quot; aby pobrać z KRS.</p>
          )}
          {supervisory.length > 0 && (
            <div className="mt-4 pt-3 border-t border-slate-700">
              <p className="text-xs text-slate-500 mb-2 uppercase tracking-wider">Rada Nadzorcza</p>
              <div className="space-y-2">
                {supervisory.map((m, i) => (
                  <div key={i} className="flex items-center justify-between p-2 bg-slate-700/30 rounded-lg">
                    <span className="text-sm text-white">{m.name}</span>
                    <span className="text-xs text-slate-400">{m.function}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
          {vatPartners.length > 0 && (
            <div className="mt-4 pt-3 border-t border-slate-700">
              <p className="text-xs text-slate-500 mb-2 uppercase tracking-wider">Wspólnicy (VAT)</p>
              <div className="space-y-1">
                {vatPartners.map((p, i) => (
                  <p key={i} className="text-sm text-slate-300">
                    {p.companyName || `${p.firstName || ""} ${p.lastName || ""}`.trim()}
                  </p>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* PKD + Shareholders + Capital */}
        <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
          {pkdAll.length > 0 ? (
            <div>
              <h2 className="text-lg font-semibold text-white mb-4">Kody PKD ({pkdAll.length})</h2>
              <div className="space-y-1 max-h-48 overflow-y-auto">
                {pkdAll.map((p, i) => (
                  <div key={i} className={`flex gap-2 text-sm p-1.5 rounded ${i === 0 ? "bg-blue-500/10 border border-blue-500/20" : ""}`}>
                    <span className="font-mono text-blue-400 flex-shrink-0 w-14">{p.code}</span>
                    <span className="text-slate-300 text-xs">{p.desc || "—"}</span>
                    {i === 0 && <span className="text-xs text-blue-400 flex-shrink-0">(główny)</span>}
                  </div>
                ))}
              </div>
            </div>
          ) : (lead.pkd || gusPkd) ? (
            <div>
              <h2 className="text-lg font-semibold text-white mb-4">PKD</h2>
              <div className="p-2 bg-blue-500/10 border border-blue-500/20 rounded-lg">
                <span className="font-mono text-blue-400">{lead.pkd || gusPkd}</span>
                {(lead.pkd_desc || gusPkdDesc) && <span className="text-sm text-slate-300 ml-2">{lead.pkd_desc || gusPkdDesc}</span>}
              </div>
              {gusPkd && lead.pkd && gusPkd !== lead.pkd && (
                <div className="mt-2 p-2 bg-slate-700/30 rounded-lg text-xs text-slate-400">
                  <span className="text-slate-500">PKD wg GUS:</span> <span className="font-mono">{gusPkd}</span> {gusPkdDesc}
                </div>
              )}
            </div>
          ) : (
            <div>
              <h2 className="text-lg font-semibold text-white mb-4">PKD</h2>
              <p className="text-slate-500 text-sm">Brak danych PKD</p>
            </div>
          )}

          {(shareholders.length > 0 || shareCapital) && (
            <div className="mt-4 pt-3 border-t border-slate-700">
              {shareCapital && (
                <div className="mb-3">
                  <p className="text-xs text-slate-500 uppercase tracking-wider">Kapitał zakładowy</p>
                  <p className="text-sm text-white font-medium">{shareCapital}</p>
                </div>
              )}
              {shareholders.length > 0 && (
                <div>
                  <p className="text-xs text-slate-500 mb-2 uppercase tracking-wider">Wspólnicy ({shareholders.length})</p>
                  <div className="space-y-2">
                    {shareholders.map((s, i) => (
                      <div key={i} className="p-2 bg-slate-700/30 rounded-lg">
                        <p className="text-sm text-white">{s.name}</p>
                        {s.shares && <p className="text-xs text-slate-400">{s.shares}</p>}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Row: Company Description + Map */}
      {(lead.description || (lead.latitude && lead.longitude)) && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
          {/* Company Description */}
          {lead.description && (
            <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
              <h2 className="text-lg font-semibold text-white mb-3">Opis firmy</h2>
              <p className="text-sm text-slate-300 whitespace-pre-wrap leading-relaxed">{lead.description}</p>
              {lead.social_media && Object.keys(lead.social_media).length > 0 && (
                <div className="mt-4 pt-3 border-t border-slate-700">
                  <p className="text-xs text-slate-500 mb-2 uppercase tracking-wider">Social Media</p>
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(lead.social_media).map(([platform, url]) => (
                      <a key={platform} href={url} target="_blank" rel="noopener noreferrer"
                        className="px-3 py-1.5 bg-blue-500/10 hover:bg-blue-500/20 text-blue-400 text-xs rounded-lg border border-blue-500/20 transition-colors capitalize">
                        {platform}
                      </a>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
          {/* Map */}
          {lead.latitude && lead.longitude && (
            <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-2 min-h-[300px]">
              <LeadMap
                latitude={lead.latitude}
                longitude={lead.longitude}
                name={lead.name}
                address={[lead.street, lead.postal_code, lead.city].filter(Boolean).join(", ")}
              />
            </div>
          )}
        </div>
      )}

      {/* Row 3: Contact + Bank Accounts + OSINT Sources + Notes */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-4">
        {/* Contact & People */}
        <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
          <h2 className="text-lg font-semibold text-white mb-4">Kontakt</h2>
          <div className="space-y-3 text-sm">
            <FirmoRow label="Firma" value={lead.contact_company || lead.name} />
            <FirmoRow label="Osoba kontaktowa" value={lead.contact_person} />
            {lead.contact_phone ? (
              <div>
                <p className="text-slate-500 text-xs mb-0.5">Telefon</p>
                <a href={`tel:${lead.contact_phone}`} className="text-blue-400 hover:text-blue-300 text-sm">{lead.contact_phone}</a>
              </div>
            ) : (
              <FirmoRow label="Telefon" value={null} />
            )}
            {lead.contact_email ? (
              <div>
                <p className="text-slate-500 text-xs mb-0.5">Email</p>
                <a href={`mailto:${lead.contact_email}`} className="text-blue-400 hover:text-blue-300 text-sm">{lead.contact_email}</a>
              </div>
            ) : (
              <FirmoRow label="Email" value={null} />
            )}
            {lead.street && (
              <FirmoRow label="Adres" value={[lead.street, lead.postal_code, lead.city].filter(Boolean).join(", ")} />
            )}
          </div>
          {/* Board members as contacts — use demasked board variable */}
          {board.length > 0 && (
            <div className="mt-4 pt-3 border-t border-slate-700">
              <p className="text-xs text-slate-500 mb-2 uppercase tracking-wider">Osoby w firmie</p>
              <div className="space-y-2">
                {board.map((m, i) => (
                  <div key={i} className="flex items-center justify-between p-2 bg-slate-700/30 rounded-lg">
                    <span className="text-sm text-white font-medium">{m.name}</span>
                    <span className="text-xs text-blue-400">{m.function}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
          {bankAccounts.length > 0 && (
            <div className="mt-4 pt-3 border-t border-slate-700">
              <p className="text-xs text-slate-500 mb-2 uppercase tracking-wider">Konta bankowe ({bankAccounts.length})</p>
              <div className="space-y-1 max-h-32 overflow-y-auto">
                {bankAccounts.map((acc, i) => (
                  <p key={i} className="text-xs font-mono text-slate-400 bg-slate-700/30 p-1.5 rounded">{String(acc)}</p>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* OSINT Sources */}
        <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
          <h2 className="text-lg font-semibold text-white mb-4">Źródła OSINT</h2>
          <div className="space-y-3">
            {["vat_whitelist", "ekrs", "ceidg", "gus"].map((src) => {
              const raw = lead.osint_raw?.[src] as Record<string, unknown> | undefined;
              const hasData = lead.sources?.includes(src);
              const hasError = raw && "error" in raw;
              return (
                <div key={src} className={`flex items-center gap-3 p-3 rounded-lg ${hasData ? "bg-emerald-500/10 border border-emerald-500/20" : hasError ? "bg-amber-500/10 border border-amber-500/20" : "bg-slate-700/30 border border-slate-700"}`}>
                  <div className={`w-2 h-2 rounded-full flex-shrink-0 ${hasData ? "bg-emerald-400" : hasError ? "bg-amber-400" : "bg-slate-600"}`} />
                  <div className="flex-1 min-w-0">
                    <p className={`text-sm font-medium ${hasData ? "text-emerald-400" : hasError ? "text-amber-400" : "text-slate-500"}`}>
                      {sourceLabels[src] || src}
                    </p>
                    {hasError && (
                      <p className="text-xs text-amber-500/70">{String(raw?.error) === "no_api_key" ? "Brak klucza API" : String(raw?.error)}</p>
                    )}
                  </div>
                  <span className={`text-xs ${hasData ? "text-emerald-500" : hasError ? "text-amber-500" : "text-slate-600"}`}>
                    {hasData ? "OK" : hasError ? "Pominięto" : "Brak danych"}
                  </span>
                </div>
              );
            })}
          </div>
          <button
            onClick={() => setShowOsintRaw(!showOsintRaw)}
            className="mt-4 text-xs text-slate-500 hover:text-slate-300 transition-colors"
          >
            {showOsintRaw ? "Ukryj surowe dane" : "Pokaż surowe dane OSINT"}
          </button>
          {showOsintRaw && lead.osint_raw && (
            <pre className="mt-2 p-3 bg-slate-900 rounded-lg text-xs text-slate-400 overflow-x-auto max-h-64 overflow-y-auto">
              {JSON.stringify(lead.osint_raw, null, 2)}
            </pre>
          )}
        </div>

        {/* Notes */}
        <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-white">Notatki</h2>
            {!editingNotes && (
              <button onClick={() => setEditingNotes(true)} className="text-xs text-blue-400 hover:text-blue-300">Edytuj</button>
            )}
          </div>
          {editingNotes ? (
            <div>
              <textarea
                value={notesValue}
                onChange={(e) => setNotesValue(e.target.value)}
                rows={6}
                className="w-full px-3 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-white text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none resize-none"
                placeholder="Dodaj notatki..."
              />
              <div className="flex gap-2 mt-2">
                <button onClick={saveNotes} className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white text-xs rounded-lg transition-colors">Zapisz</button>
                <button onClick={() => { setEditingNotes(false); setNotesValue(lead.notes || ""); }} className="px-3 py-1.5 bg-slate-700 hover:bg-slate-600 text-slate-300 text-xs rounded-lg transition-colors">Anuluj</button>
              </div>
            </div>
          ) : (
            <p className="text-slate-300 text-sm whitespace-pre-wrap">{lead.notes || "Brak notatek. Kliknij 'Edytuj' aby dodać."}</p>
          )}

          {/* AI Summary */}
          {lead.ai_summary && (
            <div className="mt-4 pt-3 border-t border-slate-700">
              <p className="text-xs text-purple-400 font-medium mb-1">AI Summary</p>
              <p className="text-sm text-slate-300">{lead.ai_summary}</p>
            </div>
          )}
        </div>
      </div>

      {/* Row 4: Scoring History */}
      {history.length > 0 && (
        <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6 mb-4">
          <h2 className="text-lg font-semibold text-white mb-4">Historia scoringu</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-slate-400 border-b border-slate-700">
                  <th className="text-left py-2 pr-4 font-medium">Data</th>
                  <th className="text-center py-2 px-4 font-medium">Score</th>
                  <th className="text-center py-2 px-4 font-medium">Tier</th>
                  <th className="text-right py-2 pl-4 font-medium">Potencjał roczny</th>
                </tr>
              </thead>
              <tbody>
                {history.map((h) => {
                  const hti = tierInfo[h.tier];
                  return (
                    <tr key={h.id} className="border-b border-slate-700/50">
                      <td className="py-2 pr-4 text-slate-300">
                        {new Date(h.scored_at).toLocaleString("pl-PL", { year: "numeric", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}
                      </td>
                      <td className="py-2 px-4 text-center text-white font-bold">{h.score}</td>
                      <td className="py-2 px-4 text-center">
                        <span className={`inline-block px-2 py-0.5 rounded text-xs font-bold border ${hti?.bg}/20 ${hti?.color} ${hti?.border}`}>
                          {h.tier}
                        </span>
                      </td>
                      <td className="py-2 pl-4 text-right text-slate-300">{(h.annual_potential / 1000).toFixed(0)}k PLN</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Row 5: Quick actions bar */}
      <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-4 flex flex-wrap gap-3 items-center">
        <span className="text-sm text-slate-400 mr-2">Szybkie akcje:</span>
        <button onClick={handleEnrich} disabled={enriching} className="px-3 py-1.5 bg-purple-600/20 hover:bg-purple-600/40 text-purple-400 text-xs rounded-lg border border-purple-600/30 transition-colors">
          {enriching ? "Trwa..." : "Tylko OSINT Enrich"}
        </button>
        <button onClick={handleScore} disabled={scoring} className="px-3 py-1.5 bg-blue-600/20 hover:bg-blue-600/40 text-blue-400 text-xs rounded-lg border border-blue-600/30 transition-colors">
          {scoring ? "Trwa..." : "Tylko Scoring"}
        </button>
        {lead.website && (
          <a href={lead.website.startsWith("http") ? lead.website : `https://${lead.website}`} target="_blank" rel="noopener noreferrer"
            className="px-3 py-1.5 bg-slate-700/50 hover:bg-slate-700 text-slate-300 text-xs rounded-lg border border-slate-600 transition-colors">
            Otwórz stronę WWW
          </a>
        )}
        <a href={`https://www.google.com/search?q=${encodeURIComponent(lead.name + " " + (lead.city || ""))}`} target="_blank" rel="noopener noreferrer"
          className="px-3 py-1.5 bg-slate-700/50 hover:bg-slate-700 text-slate-300 text-xs rounded-lg border border-slate-600 transition-colors">
          Szukaj w Google
        </a>
        <a href={`https://rejestr.io/krs?q=${encodeURIComponent(lead.nip || lead.name)}`} target="_blank" rel="noopener noreferrer"
          className="px-3 py-1.5 bg-slate-700/50 hover:bg-slate-700 text-slate-300 text-xs rounded-lg border border-slate-600 transition-colors">
          Rejestr.io
        </a>
        <a href={`https://panoramafirm.pl/szukaj?k=${encodeURIComponent(lead.name)}`} target="_blank" rel="noopener noreferrer"
          className="px-3 py-1.5 bg-slate-700/50 hover:bg-slate-700 text-slate-300 text-xs rounded-lg border border-slate-600 transition-colors">
          Panorama Firm
        </a>
      </div>
    </div>
  );
}

function FirmoRow({ label, value, mono, link, highlight }: {
  label: string;
  value: string | null | undefined;
  mono?: boolean;
  link?: boolean;
  highlight?: "green" | "yellow" | "red";
}) {
  const highlightClass = highlight === "green" ? "text-emerald-400" : highlight === "yellow" ? "text-amber-400" : highlight === "red" ? "text-red-400" : "";
  return (
    <div>
      <p className="text-slate-500 text-xs mb-0.5">{label}</p>
      {link && value ? (
        <a href={value.startsWith("http") ? value : `https://${value}`} target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:text-blue-300 text-sm truncate block">
          {value}
        </a>
      ) : (
        <p className={`text-sm ${value ? (highlightClass || "text-white") : "text-slate-600"} ${mono ? "font-mono" : ""} truncate`}>
          {value || "—"}
        </p>
      )}
    </div>
  );
}

