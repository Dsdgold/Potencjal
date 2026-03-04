"use client";

import { useEffect, useState, ReactNode } from "react";
import { useParams, useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api";
import Link from "next/link";
import dynamic from "next/dynamic";

const LeadMap = dynamic(() => import("@/components/lead-map"), { ssr: false });
const AiChat = dynamic(() => import("@/components/ai-chat"), { ssr: false });

// ── Types ──

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
  board_members: Array<{ name: string; function: string }> | null;
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

// ── Constants ──

const TIER: Record<string, { color: string; bg: string; border: string; grad: string; label: string; action: string; ring: string }> = {
  S: { color: "text-emerald-400", bg: "bg-emerald-500", border: "border-emerald-500/30", grad: "from-emerald-500/20 to-emerald-900/10", label: "PREMIUM", action: "Priorytetowy kontakt osobisty — zadzwon dzis!", ring: "#10b981" },
  A: { color: "text-blue-400", bg: "bg-blue-500", border: "border-blue-500/30", grad: "from-blue-500/20 to-blue-900/10", label: "WYSOKI", action: "Oferta rabatu ilosciowego, dostawa 24-48h", ring: "#3b82f6" },
  B: { color: "text-amber-400", bg: "bg-amber-500", border: "border-amber-500/30", grad: "from-amber-500/20 to-amber-900/10", label: "SREDNI", action: "Kampania remarketingowa, follow-up 7 dni", ring: "#f59e0b" },
  C: { color: "text-slate-400", bg: "bg-slate-500", border: "border-slate-500/30", grad: "from-slate-500/20 to-slate-900/10", label: "NISKI", action: "Monitoruj, follow-up 30 dni", ring: "#64748b" },
};

const REV_BAND: Record<string, string> = {
  micro: "< 2M PLN (mikro)",
  small: "2-10M PLN (mala)",
  medium: "10-50M PLN (srednia)",
  large: "> 50M PLN (duza)",
};

const SRC_LABEL: Record<string, { name: string; tip: string }> = {
  vat_whitelist: { name: "Biala Lista VAT", tip: "Ministerstwo Finansow — status VAT, konta bankowe, reprezentanci" },
  ekrs: { name: "eKRS", tip: "Min. Sprawiedliwosci — KRS, zarzad, kapital, PKD, forma prawna" },
  ceidg: { name: "CEIDG", tip: "biznes.gov.pl — jednoosobowe dzialalnosci gospodarcze" },
  gus: { name: "GUS REGON", tip: "stat.gov.pl — REGON, PKD, adres, forma prawna" },
};

// ── Helper: check if name is RODO-masked ──
function isMasked(s: string | null | undefined): boolean {
  return !!s && s.includes("*");
}

function clean(s: string | null | undefined): string {
  if (!s) return "";
  return s;
}

// ── Tooltip component ──
function Tip({ children, text }: { children: ReactNode; text: string }) {
  return (
    <span className="group/tip relative inline-flex items-center gap-1 cursor-help">
      {children}
      <svg className="w-3.5 h-3.5 text-slate-500 group-hover/tip:text-slate-300 transition-colors flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <circle cx="12" cy="12" r="10" />
        <path d="M12 16v-4M12 8h.01" />
      </svg>
      <span className="invisible group-hover/tip:visible opacity-0 group-hover/tip:opacity-100 transition-all absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-2 bg-slate-800 border border-slate-600 rounded-lg text-xs text-slate-300 whitespace-nowrap z-50 shadow-xl max-w-xs">
        {text}
        <span className="absolute top-full left-1/2 -translate-x-1/2 -mt-px border-4 border-transparent border-t-slate-600" />
      </span>
    </span>
  );
}

// ── Card wrapper ──
function Card({ children, className = "", hover = false }: { children: ReactNode; className?: string; hover?: boolean }) {
  return (
    <div className={`bg-slate-800/60 backdrop-blur-sm border border-slate-700/50 rounded-2xl p-5 ${hover ? "hover:border-slate-600 hover:bg-slate-800/80 transition-all duration-200" : ""} ${className}`}>
      {children}
    </div>
  );
}

// ── Data field ──
function Field({
  label,
  value,
  tip,
  mono,
  href,
  highlight,
  icon,
  onClick,
  masked,
}: {
  label: string;
  value: string | null | undefined;
  tip?: string;
  mono?: boolean;
  href?: string;
  highlight?: "green" | "yellow" | "red" | "blue";
  icon?: ReactNode;
  onClick?: () => void;
  masked?: boolean;
}) {
  const hc = highlight === "green" ? "text-emerald-400" : highlight === "yellow" ? "text-amber-400" : highlight === "red" ? "text-red-400" : highlight === "blue" ? "text-blue-400" : "";

  return (
    <div className={`group ${onClick ? "cursor-pointer" : ""}`} onClick={onClick}>
      <div className="flex items-center gap-1 mb-0.5">
        {icon && <span className="text-slate-500">{icon}</span>}
        {tip ? (
          <Tip text={tip}><span className="text-[11px] text-slate-500 uppercase tracking-wider font-medium">{label}</span></Tip>
        ) : (
          <span className="text-[11px] text-slate-500 uppercase tracking-wider font-medium">{label}</span>
        )}
      </div>
      {href && value ? (
        <a
          href={href.startsWith("http") ? href : `https://${href}`}
          target="_blank"
          rel="noopener noreferrer"
          className="text-sm text-blue-400 hover:text-blue-300 hover:underline truncate block transition-colors"
          onClick={(e) => e.stopPropagation()}
        >
          {value}
        </a>
      ) : (
        <div className="flex items-center gap-2">
          <p className={`text-sm truncate ${value ? (masked ? "text-slate-400 italic" : (hc || "text-white")) : "text-slate-600 italic"} ${mono ? "font-mono" : ""} ${onClick ? "group-hover:text-blue-400 transition-colors" : ""}`}>
            {value || "brak"}
          </p>
          {masked && <span className="text-[10px] text-amber-500 bg-amber-500/10 px-1.5 py-0.5 rounded flex-shrink-0">RODO</span>}
        </div>
      )}
    </div>
  );
}

// ── Badge ──
function Badge({ text, color = "slate" }: { text: string; color?: "emerald" | "blue" | "amber" | "red" | "purple" | "slate" }) {
  const cls: Record<string, string> = {
    emerald: "bg-emerald-500/15 text-emerald-400 border-emerald-500/25",
    blue: "bg-blue-500/15 text-blue-400 border-blue-500/25",
    amber: "bg-amber-500/15 text-amber-400 border-amber-500/25",
    red: "bg-red-500/15 text-red-400 border-red-500/25",
    purple: "bg-purple-500/15 text-purple-400 border-purple-500/25",
    slate: "bg-slate-700/50 text-slate-400 border-slate-600/50",
  };
  return <span className={`inline-flex px-2.5 py-0.5 rounded-full text-xs font-medium border ${cls[color]}`}>{text}</span>;
}

// ── Main page ──

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

      try {
        const scoreRes = await apiFetch(`/api/v1/scoring/leads/${id}`, { method: "POST" });
        if (scoreRes.ok) {
          const scoreData: ScoringResult = await scoreRes.json();
          setScoringResult(scoreData);
          setLead((prev) => prev ? { ...prev, score: scoreData.score, tier: scoreData.tier, annual_potential: scoreData.annual_potential, revenue_band: scoreData.revenue_band } : prev);
          const hRes = await apiFetch(`/api/v1/scoring/leads/${id}/history`);
          if (hRes.ok) setHistory(await hRes.json());
        }
      } catch { /* scoring auto-trigger failed */ }
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
      if (res2.ok) { const d = await res2.json(); setLead(d); setNotesValue(d.notes || ""); }
    }
    setEnriching(false);
  };

  const handleEnrichAndScore = async () => {
    setEnriching(true);
    setScoring(true);
    await apiFetch(`/api/v1/osint/enrich/${id}`, { method: "POST" });
    const res2 = await apiFetch(`/api/v1/leads/${id}`);
    if (res2.ok) { const d = await res2.json(); setLead(d); setNotesValue(d.notes || ""); }
    setEnriching(false);
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
    if (!confirm("Na pewno usunac tego leada?")) return;
    const res = await apiFetch(`/api/v1/leads/${id}`, { method: "DELETE" });
    if (res.ok) router.push("/leads");
  };

  const saveNotes = async () => {
    const res = await apiFetch(`/api/v1/leads/${id}`, { method: "PUT", body: JSON.stringify({ notes: notesValue }) });
    if (res.ok) { setLead((prev) => prev ? { ...prev, notes: notesValue } : prev); setEditingNotes(false); }
  };

  if (loading) return <div className="flex items-center justify-center h-64 text-slate-400"><div className="w-6 h-6 border-2 border-slate-400 border-t-transparent rounded-full animate-spin mr-3" />Ladowanie danych firmy...</div>;
  if (!lead) return <div className="text-red-400 p-8 text-center">Lead nie znaleziony</div>;

  // ── Extract data ──
  const ti = lead.tier ? TIER[lead.tier] : null;
  const scorePercent = lead.score ?? 0;
  const circ = 2 * Math.PI * 54;
  const dashOff = circ - (circ * scorePercent) / 100;

  const vatRaw = lead.osint_raw?.vat_whitelist as Record<string, unknown> | undefined;
  const vatSubject = vatRaw?.result ? (vatRaw.result as Record<string, unknown>)?.subject as Record<string, unknown> | undefined : undefined;
  const ekrsParsed = (lead.osint_raw?.ekrs as Record<string, unknown> | undefined)?._parsed as Record<string, unknown> | undefined;
  const gusParsed = (lead.osint_raw?.gus as Record<string, unknown> | undefined)?._parsed as Record<string, unknown> | undefined;

  const boardOrganName = ekrsParsed?.board_organ_name as string || "Zarzad";
  const rawSupervisory = (ekrsParsed?.supervisory as Array<{ name: string; function: string }>) || [];
  const supervisory = rawSupervisory.filter((m) => m.name);
  const shareholders = ((ekrsParsed?.shareholders as Array<{ name: string; shares: string }>) || []).filter((m) => m.name);
  const shareCapital = ekrsParsed?.capital as string | null;
  const pkdAll = (ekrsParsed?.pkd_all as Array<{ code: string; desc: string }>) || [];
  const legalForm = ekrsParsed?.legal_form as string | null;

  const vatRepresentatives = (vatSubject?.representatives as Array<{ firstName?: string; lastName?: string; companyName?: string }>) || [];
  const vatPartners = (vatSubject?.partners as Array<{ firstName?: string; lastName?: string; companyName?: string }>) || [];

  // Board: prefer clean names, but KEEP masked names if no clean alternative
  const savedBoard = (lead.board_members || []).filter((m) => m.name);
  const ekrsBoard = ((ekrsParsed?.board as Array<{ name: string; function: string }>) || []).filter((m) => m.name);
  const vatBoardFallback = [
    ...vatRepresentatives
      .map((r) => ({ name: (r.companyName || `${r.firstName || ""} ${r.lastName || ""}`.trim()) || "", function: "Reprezentant" }))
      .filter((m) => m.name),
    ...vatPartners
      .map((p) => ({ name: (p.companyName || `${p.firstName || ""} ${p.lastName || ""}`.trim()) || "", function: "Wspolnik" }))
      .filter((m) => m.name),
  ];
  const board = savedBoard.length > 0 ? savedBoard : ekrsBoard.length > 0 ? ekrsBoard : vatBoardFallback;

  const bankAccounts = Array.isArray(vatSubject?.accountNumbers) ? vatSubject.accountNumbers as string[] : [];
  const residenceAddress = vatSubject?.residenceAddress ? String(vatSubject.residenceAddress) : null;
  const workingAddress = vatSubject?.workingAddress ? String(vatSubject.workingAddress) : null;
  const regDate = vatSubject?.registrationLegalDate ? String(vatSubject.registrationLegalDate) : ekrsParsed?.registration_date as string | null;
  const regon = vatSubject?.regon ? String(vatSubject.regon) : gusParsed?.regon ? String(gusParsed.regon) : null;
  const krsNum = vatSubject?.krs ? String(vatSubject.krs) : gusParsed?.krs ? String(gusParsed.krs) : null;
  const gusLegalForm = gusParsed?.legal_form ? String(gusParsed.legal_form) : null;
  const gusPkd = gusParsed?.pkd ? String(gusParsed.pkd) : null;
  const gusPkdDesc = gusParsed?.pkd_desc ? String(gusParsed.pkd_desc) : null;
  const gusVoivodeship = gusParsed?.voivodeship ? String(gusParsed.voivodeship) : null;

  const fullAddress = [lead.street, lead.postal_code, lead.city].filter(Boolean).join(", ");

  // ── Render ──
  return (
    <div className="max-w-7xl mx-auto space-y-5">

      {/* ═══ HEADER ═══ */}
      <div className="flex items-start gap-4">
        <Link href="/leads" className="mt-3 p-2 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-white transition-all">
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" /></svg>
        </Link>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3 mb-1.5 flex-wrap">
            <h1 className="text-2xl font-bold text-white truncate">{lead.name}</h1>
            {lead.tier && <Badge text={`Tier ${lead.tier} — ${ti?.label}`} color={lead.tier === "S" ? "emerald" : lead.tier === "A" ? "blue" : lead.tier === "B" ? "amber" : "slate"} />}
            <Badge
              text={lead.vat_status || "VAT nieznany"}
              color={lead.vat_status === "Czynny VAT" ? "emerald" : lead.vat_status === "Zwolniony" ? "amber" : "red"}
            />
            <Badge text={lead.status} color="slate" />
          </div>
          <div className="flex items-center gap-3 text-sm text-slate-400 flex-wrap">
            <Tip text="Numer Identyfikacji Podatkowej — kliknij aby sprawdzic w rejestr.io">
              <a href={`https://rejestr.io/krs?q=${lead.nip}`} target="_blank" rel="noopener noreferrer" className="font-mono text-blue-400 hover:text-blue-300 hover:underline transition-colors">
                NIP: {lead.nip}
              </a>
            </Tip>
            {(lead.regon || regon) && (
              <Tip text="Numer REGON — identyfikator w rejestrze GUS">
                <span className="font-mono">REGON: {lead.regon || regon}</span>
              </Tip>
            )}
            {(lead.krs || krsNum) && (
              <Tip text="Numer KRS — Krajowy Rejestr Sadowy, kliknij aby sprawdzic">
                <a href={`https://ekrs.ms.gov.pl/web/wyszukiwarka-krs/strona-glowna/index.html`} target="_blank" rel="noopener noreferrer" className="font-mono text-blue-400 hover:text-blue-300 hover:underline transition-colors">
                  KRS: {lead.krs || krsNum}
                </a>
              </Tip>
            )}
            {lead.city && <span>{lead.city}{lead.voivodeship ? `, woj. ${lead.voivodeship}` : ""}</span>}
          </div>
        </div>
        <div className="flex gap-2 flex-shrink-0">
          <Link href={`/leads/${id}/edit`} className="px-4 py-2 bg-slate-700/70 hover:bg-slate-600 text-white text-sm rounded-xl transition-all hover:shadow-lg">
            Edytuj
          </Link>
          <button onClick={handleDelete} className="px-4 py-2 bg-red-600/15 hover:bg-red-600/30 text-red-400 text-sm rounded-xl border border-red-600/20 transition-all">
            Usun
          </button>
        </div>
      </div>

      {/* ═══ ENRICH BAR ═══ */}
      <div className="bg-gradient-to-r from-emerald-900/20 to-blue-900/20 border border-emerald-500/20 rounded-2xl p-4 flex items-center justify-between gap-4">
        <div className="flex-1 min-w-0">
          <p className="text-sm text-emerald-300 font-medium">
            {enriching ? "Pobieranie danych z rejestrow, stron WWW i map..." : scoring ? "Obliczanie scoringu..." : "Wzbogac dane firmy z rejestrow publicznych"}
          </p>
          <Tip text="Dane pobierane z: Biala Lista VAT, eKRS, GUS REGON, CEIDG, strona WWW firmy, Panorama Firm, Aleo, Google">
            <p className="text-xs text-slate-400 mt-0.5">
              VAT + eKRS + GUS + CEIDG + WWW + Panorama Firm + Aleo + Google + Geolokalizacja
            </p>
          </Tip>
        </div>
        <button
          onClick={handleEnrichAndScore}
          disabled={enriching || scoring}
          className="px-6 py-3 bg-emerald-600 hover:bg-emerald-500 disabled:bg-emerald-600/40 text-white text-sm rounded-xl transition-all font-bold whitespace-nowrap shadow-lg shadow-emerald-900/30 hover:shadow-emerald-900/50 hover:scale-[1.02] active:scale-[0.98]"
        >
          {enriching ? "Pobieranie..." : scoring ? "Scoring..." : "Wzbogac dane + Scoring"}
        </button>
      </div>

      {/* ═══ ROW 1: Score + Action + Potential ═══ */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-5">

        {/* Score Ring */}
        <Card className={`flex flex-col items-center justify-center bg-gradient-to-b ${ti?.grad || "from-slate-800/50 to-slate-900/30"}`}>
          <Tip text="Scoring 0-100 obliczany na podstawie 7 czynnikow wazonych: pracownicy, przychody, lata na rynku, VAT, PKD, koszyk, lokalizacja">
            <span className="text-[11px] text-slate-500 uppercase tracking-wider font-medium mb-3">Score</span>
          </Tip>
          <div className="relative w-32 h-32 mb-3">
            <svg className="w-32 h-32 -rotate-90" viewBox="0 0 120 120">
              <circle cx="60" cy="60" r="54" fill="none" stroke="#1e293b" strokeWidth="8" />
              <circle
                cx="60" cy="60" r="54" fill="none"
                stroke={ti?.ring || "#475569"}
                strokeWidth="8" strokeLinecap="round"
                strokeDasharray={circ} strokeDashoffset={dashOff}
                className="transition-all duration-1000 ease-out"
              />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className={`text-4xl font-black ${ti?.color || "text-slate-400"}`}>{lead.score ?? "—"}</span>
              <span className="text-[11px] text-slate-500">/100 pkt</span>
            </div>
          </div>
          {lead.tier && <Badge text={`Tier ${lead.tier}`} color={lead.tier === "S" ? "emerald" : lead.tier === "A" ? "blue" : lead.tier === "B" ? "amber" : "slate"} />}
        </Card>

        {/* Recommended Action */}
        <Card className="lg:col-span-2" hover>
          <Tip text="Rekomendacja handlowa generowana na podstawie tier scoringowego i profilu firmy">
            <h3 className="text-[11px] text-slate-500 uppercase tracking-wider font-medium mb-3">Rekomendowana akcja</h3>
          </Tip>
          {ti ? (
            <p className={`text-lg font-semibold ${ti.color} mb-3 leading-snug`}>{ti.action}</p>
          ) : (
            <p className="text-slate-500">Przelicz scoring aby otrzymac rekomendacje</p>
          )}
          {scoringResult?.recommended_actions && scoringResult.recommended_actions.length > 0 && (
            <ul className="space-y-1.5 mt-2">
              {scoringResult.recommended_actions.map((a, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-slate-300">
                  <span className={`mt-1 w-1.5 h-1.5 rounded-full flex-shrink-0 ${ti?.bg || "bg-slate-500"}`} /> {a}
                </li>
              ))}
            </ul>
          )}
          {scoringResult?.categories && scoringResult.categories.length > 0 && (
            <div className="mt-4 flex flex-wrap gap-1.5">
              <Tip text="Kategorie produktow budowlanych dopasowane na podstawie kodu PKD firmy">
                <span className="text-[10px] text-slate-500 mr-1">Kategorie:</span>
              </Tip>
              {scoringResult.categories.map((c, i) => (
                <Badge key={i} text={c} color="blue" />
              ))}
            </div>
          )}
        </Card>

        {/* Potential */}
        <Card hover>
          <Tip text="Szacowany roczny potencjal zakupowy = bazowe ARPU (18 000 PLN) x mnoznik tier (S:30x, A:12x, B:5x, C:2x)">
            <h3 className="text-[11px] text-slate-500 uppercase tracking-wider font-medium mb-2">Potencjal roczny</h3>
          </Tip>
          <p className="text-3xl font-black text-white">
            {lead.annual_potential ? `${(lead.annual_potential / 1000).toFixed(0)}k` : "—"}
            <span className="text-base font-normal text-slate-500 ml-1">PLN</span>
          </p>
          {lead.revenue_band && (
            <Tip text="Pasmo przychodowe na podstawie danych z rejestrow: micro (<2M), small (2-10M), medium (10-50M), large (>50M)">
              <p className="text-sm text-slate-400 mt-2">{REV_BAND[lead.revenue_band] || lead.revenue_band}</p>
            </Tip>
          )}
          <div className="mt-4 grid grid-cols-2 gap-2">
            <div className="bg-slate-700/30 rounded-xl p-2.5 text-center">
              <Tip text="Aktualny status leada w pipeline"><p className="text-[10px] text-slate-500 mb-0.5">Status</p></Tip>
              <p className="text-white text-sm font-medium capitalize">{lead.status}</p>
            </div>
            <div className="bg-slate-700/30 rounded-xl p-2.5 text-center">
              <Tip text="Ile rejestrow publicznych zwrocilo dane"><p className="text-[10px] text-slate-500 mb-0.5">Zrodla</p></Tip>
              <p className="text-white text-sm font-medium">{lead.sources?.length || 0} rej.</p>
            </div>
          </div>
        </Card>
      </div>

      {/* ═══ ROW 2: Scoring Breakdown + Firmography ═══ */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">

        {/* Scoring Breakdown */}
        <Card>
          <div className="flex items-center justify-between mb-4">
            <Tip text="Scoring skladniowy: kazdy czynnik ma wage (procent) i wynik surowy (0-100). Suma wazona = koncowy score.">
              <h2 className="text-base font-semibold text-white">Scoring — rozklad czynnikow</h2>
            </Tip>
            <button onClick={handleScore} disabled={scoring} className="text-xs text-blue-400 hover:text-blue-300 transition-colors px-3 py-1.5 rounded-lg hover:bg-blue-500/10">
              {scoring ? "Liczenie..." : "Przelicz"}
            </button>
          </div>
          {scoringResult?.breakdown ? (
            <div className="space-y-3">
              {scoringResult.breakdown.map((b) => {
                const tips: Record<string, string> = {
                  employees: "Liczba pracownikow: <=9 = 20 pkt, <=49 = 55, <=249 = 78, >249 = 92",
                  revenueBand: "Pasmo przychodowe: micro = 25, small = 55, medium = 75, large = 92",
                  yearsActive: "Lata na rynku: <=1 = 20, <=3 = 40, <=7 = 60, <=12 = 75, >12 = 88",
                  vatStatus: "Czynny VAT = 80 pkt, Zwolniony = 55, Niepewny = 35",
                  pkdFit: "Dopasowanie PKD do branz budowlanej + korekta wg rozmiaru firmy",
                  basketSignal: "Sygnal koszykowy: 30 + (min(1, koszyk/8000)^0.65) x 60",
                  locality: "Lokalizacja: duze miasta (7 miast) = 75 pkt, inne = 55",
                };
                return (
                  <div key={b.factor} className="group/bar">
                    <div className="flex justify-between text-sm mb-1">
                      <Tip text={tips[b.factor] || `Czynnik: ${b.factor}`}>
                        <span className="text-slate-300 group-hover/bar:text-white transition-colors">{b.label}</span>
                      </Tip>
                      <span className="text-slate-400 tabular-nums">
                        <span className="text-white font-semibold">{b.raw_score}</span>/100 x {(b.weight * 100).toFixed(0)}% = <span className="text-white font-semibold">{b.weighted_score.toFixed(1)}</span>
                      </span>
                    </div>
                    <div className="h-2.5 bg-slate-700/50 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all duration-700 ease-out ${b.raw_score >= 70 ? "bg-gradient-to-r from-emerald-600 to-emerald-400" : b.raw_score >= 50 ? "bg-gradient-to-r from-blue-600 to-blue-400" : b.raw_score >= 30 ? "bg-gradient-to-r from-amber-600 to-amber-400" : "bg-gradient-to-r from-red-600 to-red-400"}`}
                        style={{ width: `${b.raw_score}%` }}
                      />
                    </div>
                  </div>
                );
              })}
              <div className="border-t border-slate-700/50 pt-3 mt-4 flex justify-between text-sm">
                <span className="text-slate-400 font-medium">Suma wazona</span>
                <span className="text-white font-black text-lg">{lead.score ?? "—"}<span className="text-slate-500 text-sm font-normal"> / 100</span></span>
              </div>
            </div>
          ) : (
            <div className="text-center py-10">
              <p className="text-slate-500 mb-3">Kliknij aby zobaczyc rozklad scoringu</p>
              <button onClick={handleScore} disabled={scoring} className="px-5 py-2.5 bg-blue-600 hover:bg-blue-500 text-white text-sm rounded-xl transition-all hover:shadow-lg">
                Przelicz scoring
              </button>
            </div>
          )}
        </Card>

        {/* Firmography */}
        <Card>
          <Tip text="Dane firmowe zebrane z rejestrow: eKRS, GUS, CEIDG, Biala Lista VAT, strona WWW firmy">
            <h2 className="text-base font-semibold text-white mb-4">Dane firmowe</h2>
          </Tip>
          <div className="grid grid-cols-2 gap-x-6 gap-y-4">
            <Field label="Pelna nazwa" value={lead.name} tip="Nazwa firmy z KRS/CEIDG/VAT" />
            <Field label="NIP" value={lead.nip} mono tip="Numer Identyfikacji Podatkowej — unikalny identyfikator podatkowy" href={`https://rejestr.io/krs?q=${lead.nip}`} />
            <Field label="REGON" value={lead.regon || regon} mono tip="Numer REGON — identyfikator w rejestrze GUS" />
            <Field label="KRS" value={lead.krs || krsNum} mono tip="Krajowy Rejestr Sadowy — rejestr sadowy spolek" href={lead.krs || krsNum ? `https://rejestr.io/krs/${lead.krs || krsNum}` : undefined} />
            <Field label="Forma prawna" value={lead.legal_form || legalForm || gusLegalForm} tip="Forma prawna: sp. z o.o., sp.k., sp.j., S.A., JDG, itp." />
            <Field label="Adres" value={fullAddress || lead.city} tip="Adres siedziby firmy — kliknij aby otworzyc w Google Maps" href={fullAddress ? `https://www.google.com/maps/search/${encodeURIComponent(fullAddress)}` : undefined} />
            <Field label="Wojewodztwo" value={lead.voivodeship || gusVoivodeship} tip="Wojewodztwo wg rejestru GUS lub eKRS" />
            <Field label="PKD (glowny)" value={lead.pkd ? `${lead.pkd}${lead.pkd_desc ? ` — ${lead.pkd_desc}` : ""}` : gusPkd ? `${gusPkd} — ${gusPkdDesc || ""}` : null} tip="Polska Klasyfikacja Dzialalnosci — kod okresla branze firmy" />
            <Field label="Lata dzialalnosci" value={lead.years_active != null ? `${lead.years_active.toFixed(1)} lat` : null} tip="Obliczone na podstawie daty rejestracji w KRS/CEIDG" />
            <Field label="Status VAT" value={lead.vat_status} highlight={lead.vat_status === "Czynny VAT" ? "green" : lead.vat_status === "Zwolniony" ? "yellow" : "red"} tip="Czynny VAT = aktywny podatnik, Zwolniony = nie odlicza VAT" />
            <Field label="Strona WWW" value={lead.website} href={lead.website || undefined} tip="Strona internetowa firmy — kliknij aby otworzyc" />
            <Field label="Pracownicy" value={lead.employees != null ? `${lead.employees} os.` : null} tip="Szacunkowa liczba pracownikow z rejestrow lub stron branżowych" />
            <Field label="Przychod roczny" value={lead.revenue_pln ? `${(lead.revenue_pln / 1_000_000).toFixed(1)}M PLN` : null} tip="Szacunkowy roczny przychod w PLN" />
            <Field label="Pasmo przychodow" value={lead.revenue_band ? REV_BAND[lead.revenue_band] || lead.revenue_band : null} tip="Kategoria przychodowa: micro (<2M), small (2-10M), medium (10-50M), large (>50M)" />
            <Field label="Data rejestracji" value={regDate} tip="Data rejestracji w KRS lub rozpoczecia dzialalnosci w CEIDG" />
            <Field label="Kategoria" value={lead.category} tip="Kategoria biznesowa przypisana do leada" />
          </div>
        </Card>
      </div>

      {/* ═══ ROW 3: People + Contact + PKD ═══ */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">

        {/* Board / Representatives */}
        <Card>
          <Tip text="Czlonkowie zarzadu i rady nadzorczej ze zrodel: eKRS (funkcje), VAT (pelne imiona)">
            <h2 className="text-base font-semibold text-white mb-4">Zarzad i Reprezentacja</h2>
          </Tip>
          {board.length > 0 ? (
            <div>
              <p className="text-[10px] text-slate-500 mb-2 uppercase tracking-wider">{boardOrganName}</p>
              <div className="space-y-2">
                {board.map((m, i) => {
                  const masked = isMasked(m.name);
                  return (
                    <div key={i} className="flex items-center justify-between p-2.5 bg-slate-700/30 hover:bg-slate-700/50 rounded-xl transition-colors">
                      <div className="flex items-center gap-2.5">
                        <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold ${masked ? "bg-amber-500/20 text-amber-400" : "bg-slate-600/50 text-slate-300"}`}>
                          {masked ? "?" : m.name.split(" ").map(n => n[0]).join("").slice(0, 2).toUpperCase()}
                        </div>
                        <div>
                          <span className={`text-sm font-medium ${masked ? "text-slate-400 italic" : "text-white"}`}>{m.name}</span>
                          {masked && <span className="ml-2 text-[10px] text-amber-500 bg-amber-500/10 px-1.5 py-0.5 rounded">RODO</span>}
                        </div>
                      </div>
                      <Badge text={m.function || "Czlonek"} color="purple" />
                    </div>
                  );
                })}
              </div>
            </div>
          ) : (
            <p className="text-slate-500 text-sm py-4 text-center">Brak danych — kliknij &quot;Wzbogac dane&quot;</p>
          )}

          {supervisory.length > 0 && (
            <div className="mt-4 pt-3 border-t border-slate-700/50">
              <Tip text="Rada Nadzorcza — organ nadzoru spolki, dane z eKRS. Imiona zanonimizowane (RODO) przez eKRS.">
                <p className="text-[10px] text-slate-500 mb-2 uppercase tracking-wider">Rada Nadzorcza ({supervisory.length})</p>
              </Tip>
              <div className="space-y-2">
                {supervisory.map((m, i) => {
                  const masked = isMasked(m.name);
                  return (
                    <div key={i} className="flex items-center justify-between p-2 bg-slate-700/30 rounded-xl">
                      <div className="flex items-center gap-2">
                        <span className={`text-sm ${masked ? "text-slate-400 italic" : "text-white"}`}>{m.name}</span>
                        {masked && <span className="text-[10px] text-amber-500 bg-amber-500/10 px-1.5 py-0.5 rounded">RODO</span>}
                      </div>
                      <span className="text-[11px] text-slate-400">{m.function}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {shareholders.length > 0 && (
            <div className="mt-4 pt-3 border-t border-slate-700/50">
              <Tip text="Wspolnicy/udzialowcy spolki — dane z eKRS">
                <p className="text-[10px] text-slate-500 mb-2 uppercase tracking-wider">Wspolnicy ({shareholders.length})</p>
              </Tip>
              <div className="space-y-2">
                {shareholders.map((s, i) => {
                  const masked = isMasked(s.name);
                  return (
                    <div key={i} className="p-2 bg-slate-700/30 rounded-xl">
                      <div className="flex items-center gap-2">
                        <p className={`text-sm ${masked ? "text-slate-400 italic" : "text-white"}`}>{s.name}</p>
                        {masked && <span className="text-[10px] text-amber-500 bg-amber-500/10 px-1.5 py-0.5 rounded">RODO</span>}
                      </div>
                      {s.shares && <p className="text-[11px] text-slate-400 mt-0.5">{s.shares}</p>}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {shareCapital && (
            <div className="mt-3 p-2.5 bg-slate-700/20 rounded-xl">
              <Tip text="Kapital zakladowy spolki — minimalna wartosc wkladow wspolnikow">
                <p className="text-[10px] text-slate-500">Kapital zakladowy</p>
              </Tip>
              <p className="text-sm text-white font-medium">{shareCapital}</p>
            </div>
          )}
        </Card>

        {/* Contact */}
        <Card>
          <Tip text="Dane kontaktowe zebrane ze strony WWW, Panorama Firm, Aleo i rejestrow">
            <h2 className="text-base font-semibold text-white mb-4">Kontakt</h2>
          </Tip>
          <div className="space-y-4">
            <Field label="Osoba kontaktowa" value={lead.contact_person} tip="Osoba kontaktowa — najczesciej prezes/wlasciciel z KRS lub VAT" masked={isMasked(lead.contact_person)} />
            {lead.contact_phone ? (
              <div>
                <Tip text="Telefon — kliknij aby zadzwonic"><p className="text-[11px] text-slate-500 uppercase tracking-wider font-medium mb-0.5">Telefon</p></Tip>
                <a href={`tel:${lead.contact_phone}`} className="text-sm text-blue-400 hover:text-blue-300 hover:underline transition-colors flex items-center gap-2">
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" /></svg>
                  {lead.contact_phone}
                </a>
              </div>
            ) : (
              <Field label="Telefon" value={null} tip="Telefon — pobierany ze strony WWW firmy lub Panorama Firm" />
            )}
            {lead.contact_email ? (
              <div>
                <Tip text="Email — kliknij aby wyslac wiadomosc"><p className="text-[11px] text-slate-500 uppercase tracking-wider font-medium mb-0.5">Email</p></Tip>
                <a href={`mailto:${lead.contact_email}`} className="text-sm text-blue-400 hover:text-blue-300 hover:underline transition-colors flex items-center gap-2">
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" /></svg>
                  {lead.contact_email}
                </a>
              </div>
            ) : (
              <Field label="Email" value={null} tip="Email — pobierany ze strony WWW firmy lub Panorama Firm" />
            )}
            <Field label="Strona WWW" value={lead.website} href={lead.website || undefined} tip="Strona internetowa — kliknij aby otworzyc" />
            {fullAddress && (
              <Field label="Adres" value={fullAddress} href={`https://www.google.com/maps/search/${encodeURIComponent(fullAddress)}`} tip="Adres siedziby — kliknij aby otworzyc w Google Maps" />
            )}
            {(residenceAddress || workingAddress) && (
              <div className="pt-3 border-t border-slate-700/50">
                {residenceAddress && <Field label="Adres siedziby (VAT)" value={residenceAddress} tip="Adres z Bialej Listy VAT" href={`https://www.google.com/maps/search/${encodeURIComponent(residenceAddress)}`} />}
                {workingAddress && workingAddress !== residenceAddress && <Field label="Adres dzialalnosci" value={workingAddress} tip="Adres prowadzenia dzialalnosci z VAT" href={`https://www.google.com/maps/search/${encodeURIComponent(workingAddress)}`} />}
              </div>
            )}
          </div>

          {/* Social Media */}
          {lead.social_media && Object.keys(lead.social_media).length > 0 && (
            <div className="mt-4 pt-3 border-t border-slate-700/50">
              <Tip text="Linki do mediow spolecznosciowych znalezione na stronie WWW firmy">
                <p className="text-[10px] text-slate-500 mb-2 uppercase tracking-wider">Social Media</p>
              </Tip>
              <div className="flex flex-wrap gap-2">
                {Object.entries(lead.social_media).map(([platform, url]) => (
                  <a key={platform} href={url} target="_blank" rel="noopener noreferrer"
                    className="px-3 py-1.5 bg-blue-500/10 hover:bg-blue-500/20 text-blue-400 text-xs rounded-xl border border-blue-500/20 transition-all hover:scale-105 capitalize">
                    {platform}
                  </a>
                ))}
              </div>
            </div>
          )}

          {/* Bank accounts */}
          {bankAccounts.length > 0 && (
            <div className="mt-4 pt-3 border-t border-slate-700/50">
              <Tip text="Konta bankowe z Bialej Listy VAT — zweryfikowane przez MF">
                <p className="text-[10px] text-slate-500 mb-2 uppercase tracking-wider">Konta bankowe ({bankAccounts.length})</p>
              </Tip>
              <div className="space-y-1 max-h-24 overflow-y-auto">
                {bankAccounts.map((acc, i) => (
                  <p key={i} className="text-[11px] font-mono text-slate-400 bg-slate-700/30 p-1.5 rounded-lg">{String(acc)}</p>
                ))}
              </div>
            </div>
          )}
        </Card>

        {/* PKD + OSINT Sources */}
        <Card>
          {pkdAll.length > 0 ? (
            <div>
              <Tip text="Polska Klasyfikacja Dzialalnosci — lista kodow PKD z KRS (pierwszy = glowny)">
                <h2 className="text-base font-semibold text-white mb-4">Kody PKD ({pkdAll.length})</h2>
              </Tip>
              <div className="space-y-1 max-h-48 overflow-y-auto">
                {pkdAll.map((p, i) => (
                  <a key={i}
                    href={`https://www.biznes.gov.pl/pl/tabela-pkd/pkd/${p.code.replace(".", "")}`}
                    target="_blank" rel="noopener noreferrer"
                    className={`flex gap-2 text-sm p-2 rounded-xl transition-all hover:bg-slate-700/60 cursor-pointer ${i === 0 ? "bg-blue-500/10 border border-blue-500/20" : ""}`}
                  >
                    <span className="font-mono text-blue-400 flex-shrink-0 w-14">{p.code}</span>
                    <span className="text-slate-300 text-xs flex-1">{p.desc || "—"}</span>
                    {i === 0 && <Badge text="glowny" color="blue" />}
                  </a>
                ))}
              </div>
            </div>
          ) : (lead.pkd || gusPkd) ? (
            <div>
              <Tip text="Kod PKD — Polska Klasyfikacja Dzialalnosci"><h2 className="text-base font-semibold text-white mb-4">PKD</h2></Tip>
              <a href={`https://www.biznes.gov.pl/pl/tabela-pkd/pkd/${(lead.pkd || gusPkd || "").replace(".", "")}`} target="_blank" rel="noopener noreferrer"
                className="block p-3 bg-blue-500/10 border border-blue-500/20 rounded-xl hover:bg-blue-500/15 transition-colors">
                <span className="font-mono text-blue-400">{lead.pkd || gusPkd}</span>
                {(lead.pkd_desc || gusPkdDesc) && <span className="text-sm text-slate-300 ml-2">{lead.pkd_desc || gusPkdDesc}</span>}
              </a>
            </div>
          ) : null}

          {/* OSINT Sources */}
          <div className={pkdAll.length > 0 || lead.pkd ? "mt-5 pt-4 border-t border-slate-700/50" : ""}>
            <Tip text="Rejestry publiczne uzyte do wzbogacenia danych — zielony = pobrano, zolty = blad, szary = brak danych">
              <h3 className="text-[11px] text-slate-500 uppercase tracking-wider font-medium mb-3">Zrodla OSINT</h3>
            </Tip>
            <div className="space-y-2">
              {(["vat_whitelist", "ekrs", "ceidg", "gus"] as const).map((src) => {
                const raw = lead.osint_raw?.[src] as Record<string, unknown> | undefined;
                const hasData = lead.sources?.includes(src);
                const hasError = raw && "error" in raw;
                const errStr = raw ? String(raw.error) : "";
                const isCeidgNA = src === "ceidg" && (errStr === "not_found" || errStr === "not_applicable");
                const srcInfo = SRC_LABEL[src];
                return (
                  <Tip key={src} text={srcInfo.tip}>
                    <div className={`flex items-center gap-3 p-2.5 rounded-xl cursor-help w-full transition-all hover:scale-[1.01] ${hasData ? "bg-emerald-500/10 border border-emerald-500/15" : isCeidgNA ? "bg-slate-700/20 border border-slate-700/50" : hasError ? "bg-amber-500/10 border border-amber-500/15" : "bg-slate-700/20 border border-slate-700/50"}`}>
                      <div className={`w-2 h-2 rounded-full flex-shrink-0 ${hasData ? "bg-emerald-400 shadow-sm shadow-emerald-400/50" : isCeidgNA ? "bg-slate-500" : hasError ? "bg-amber-400" : "bg-slate-600"}`} />
                      <span className={`text-sm flex-1 ${hasData ? "text-emerald-400" : "text-slate-400"}`}>{srcInfo.name}</span>
                      <span className={`text-[10px] ${hasData ? "text-emerald-500" : isCeidgNA ? "text-slate-500" : hasError ? "text-amber-500" : "text-slate-600"}`}>
                        {hasData ? "OK" : isCeidgNA ? "N/D" : hasError ? "Blad" : "—"}
                      </span>
                    </div>
                  </Tip>
                );
              })}
            </div>
            <button onClick={() => setShowOsintRaw(!showOsintRaw)} className="mt-3 text-[11px] text-slate-500 hover:text-slate-300 transition-colors">
              {showOsintRaw ? "Ukryj surowe dane" : "Pokaz JSON"}
            </button>
            {showOsintRaw && lead.osint_raw && (
              <pre className="mt-2 p-3 bg-slate-900 rounded-xl text-[11px] text-slate-400 overflow-x-auto max-h-48 overflow-y-auto">
                {JSON.stringify(lead.osint_raw, null, 2)}
              </pre>
            )}
          </div>
        </Card>
      </div>

      {/* ═══ ROW 4: Description + Map ═══ */}
      {(lead.description || (lead.latitude && lead.longitude)) && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          {lead.description && (
            <Card>
              <Tip text="Opis firmy wygenerowany z danych rejestrow, strony WWW, Google i portali branżowych">
                <h2 className="text-base font-semibold text-white mb-3">Opis firmy</h2>
              </Tip>
              <p className="text-sm text-slate-300 whitespace-pre-wrap leading-relaxed">{lead.description}</p>
            </Card>
          )}
          {lead.latitude && lead.longitude && (
            <div className="bg-slate-800/60 border border-slate-700/50 rounded-2xl p-2 min-h-[300px]">
              <LeadMap latitude={lead.latitude} longitude={lead.longitude} name={lead.name} address={fullAddress} />
            </div>
          )}
        </div>
      )}

      {/* ═══ ROW 5: Notes + History ═══ */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Notes */}
        <Card>
          <div className="flex items-center justify-between mb-4">
            <Tip text="Twoje notatki do tego leada — widoczne tylko dla Ciebie">
              <h2 className="text-base font-semibold text-white">Notatki</h2>
            </Tip>
            {!editingNotes && (
              <button onClick={() => setEditingNotes(true)} className="text-xs text-blue-400 hover:text-blue-300 px-3 py-1.5 rounded-lg hover:bg-blue-500/10 transition-all">
                Edytuj
              </button>
            )}
          </div>
          {editingNotes ? (
            <div>
              <textarea
                value={notesValue}
                onChange={(e) => setNotesValue(e.target.value)}
                rows={6}
                className="w-full px-3 py-2.5 bg-slate-700/30 border border-slate-600/50 rounded-xl text-white text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none resize-none placeholder-slate-500"
                placeholder="Dodaj notatki..."
              />
              <div className="flex gap-2 mt-2">
                <button onClick={saveNotes} className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-xs rounded-xl transition-all">Zapisz</button>
                <button onClick={() => { setEditingNotes(false); setNotesValue(lead.notes || ""); }} className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-slate-300 text-xs rounded-xl transition-all">Anuluj</button>
              </div>
            </div>
          ) : (
            <p className="text-slate-300 text-sm whitespace-pre-wrap">{lead.notes || "Brak notatek."}</p>
          )}
          {lead.ai_summary && (
            <div className="mt-4 pt-3 border-t border-slate-700/50">
              <Tip text="Podsumowanie wygenerowane przez AI na podstawie danych firmy">
                <p className="text-[10px] text-purple-400 font-medium mb-1">AI Summary</p>
              </Tip>
              <p className="text-sm text-slate-300">{lead.ai_summary}</p>
            </div>
          )}
        </Card>

        {/* Scoring History */}
        <Card>
          <Tip text="Historia wszystkich przeliczen scoringu — pozwala sledzic zmiany w czasie">
            <h2 className="text-base font-semibold text-white mb-4">Historia scoringu ({history.length})</h2>
          </Tip>
          {history.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-slate-500 border-b border-slate-700/50">
                    <th className="text-left py-2 pr-4 font-medium text-[11px] uppercase tracking-wider">Data</th>
                    <th className="text-center py-2 px-4 font-medium text-[11px] uppercase tracking-wider">Score</th>
                    <th className="text-center py-2 px-4 font-medium text-[11px] uppercase tracking-wider">Tier</th>
                    <th className="text-right py-2 pl-4 font-medium text-[11px] uppercase tracking-wider">Potencjal</th>
                  </tr>
                </thead>
                <tbody>
                  {history.map((h, i) => {
                    const hti = TIER[h.tier];
                    return (
                      <tr key={h.id} className={`border-b border-slate-700/30 hover:bg-slate-700/20 transition-colors ${i === 0 ? "bg-slate-700/10" : ""}`}>
                        <td className="py-2.5 pr-4 text-slate-300 text-xs">
                          {new Date(h.scored_at).toLocaleString("pl-PL", { year: "numeric", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}
                        </td>
                        <td className="py-2.5 px-4 text-center text-white font-bold">{h.score}</td>
                        <td className="py-2.5 px-4 text-center">
                          <Badge text={h.tier} color={h.tier === "S" ? "emerald" : h.tier === "A" ? "blue" : h.tier === "B" ? "amber" : "slate"} />
                        </td>
                        <td className="py-2.5 pl-4 text-right text-slate-300">{(h.annual_potential / 1000).toFixed(0)}k PLN</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-slate-500 text-sm text-center py-8">Brak historii — przelicz scoring</p>
          )}
        </Card>
      </div>

      {/* ═══ QUICK ACTIONS BAR ═══ */}
      <Card className="flex flex-wrap gap-2.5 items-center">
        <Tip text="Szybkie akcje — linki do rejestrow i narzedzi zewnetrznych">
          <span className="text-[11px] text-slate-500 uppercase tracking-wider font-medium mr-2">Szybkie akcje</span>
        </Tip>
        <button onClick={handleEnrich} disabled={enriching} className="px-3.5 py-2 bg-purple-600/15 hover:bg-purple-600/30 text-purple-400 text-xs rounded-xl border border-purple-600/20 transition-all hover:scale-105">
          {enriching ? "Trwa..." : "Tylko OSINT Enrich"}
        </button>
        <button onClick={handleScore} disabled={scoring} className="px-3.5 py-2 bg-blue-600/15 hover:bg-blue-600/30 text-blue-400 text-xs rounded-xl border border-blue-600/20 transition-all hover:scale-105">
          {scoring ? "Trwa..." : "Tylko Scoring"}
        </button>
        {lead.website && (
          <a href={lead.website.startsWith("http") ? lead.website : `https://${lead.website}`} target="_blank" rel="noopener noreferrer"
            className="px-3.5 py-2 bg-slate-700/30 hover:bg-slate-700/60 text-slate-300 text-xs rounded-xl border border-slate-600/30 transition-all hover:scale-105">
            Strona WWW
          </a>
        )}
        <a href={`https://www.google.com/search?q=${encodeURIComponent(lead.name + " " + (lead.city || ""))}`} target="_blank" rel="noopener noreferrer"
          className="px-3.5 py-2 bg-slate-700/30 hover:bg-slate-700/60 text-slate-300 text-xs rounded-xl border border-slate-600/30 transition-all hover:scale-105">
          Google
        </a>
        <a href={`https://rejestr.io/krs?q=${encodeURIComponent(lead.nip || lead.name)}`} target="_blank" rel="noopener noreferrer"
          className="px-3.5 py-2 bg-slate-700/30 hover:bg-slate-700/60 text-slate-300 text-xs rounded-xl border border-slate-600/30 transition-all hover:scale-105">
          Rejestr.io
        </a>
        <a href={`https://panoramafirm.pl/szukaj?k=${encodeURIComponent(lead.name)}`} target="_blank" rel="noopener noreferrer"
          className="px-3.5 py-2 bg-slate-700/30 hover:bg-slate-700/60 text-slate-300 text-xs rounded-xl border border-slate-600/30 transition-all hover:scale-105">
          Panorama Firm
        </a>
        <a href={`https://aleo.com/pl/szukaj?query=${encodeURIComponent(lead.nip || lead.name)}`} target="_blank" rel="noopener noreferrer"
          className="px-3.5 py-2 bg-slate-700/30 hover:bg-slate-700/60 text-slate-300 text-xs rounded-xl border border-slate-600/30 transition-all hover:scale-105">
          Aleo
        </a>
      </Card>

      {/* AI Chat */}
      <AiChat leadId={lead.id} leadName={lead.name} />
    </div>
  );
}
