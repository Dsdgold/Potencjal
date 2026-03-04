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

const TIER: Record<string, { color: string; bg: string; border: string; label: string; action: string; ring: string }> = {
  S: { color: "text-[#22c55e]", bg: "bg-[#22c55e]", border: "border-[#22c55e]/20", label: "PREMIUM", action: "Priorytetowy kontakt osobisty — zadzwon dzis!", ring: "#22c55e" },
  A: { color: "text-[#0ea5e9]", bg: "bg-[#0ea5e9]", border: "border-[#0ea5e9]/20", label: "WYSOKI", action: "Oferta rabatu ilosciowego, dostawa 24-48h", ring: "#0ea5e9" },
  B: { color: "text-[#f59e0b]", bg: "bg-[#f59e0b]", border: "border-[#f59e0b]/20", label: "SREDNI", action: "Kampania remarketingowa, follow-up 7 dni", ring: "#f59e0b" },
  C: { color: "text-[#455566]", bg: "bg-[#455566]", border: "border-[#455566]/20", label: "NISKI", action: "Monitoruj, follow-up 30 dni", ring: "#455566" },
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

// ── Tooltip component ──
function Tip({ children, text }: { children: ReactNode; text: string }) {
  return (
    <span className="group/tip relative inline-flex items-center gap-1 cursor-help">
      {children}
      <svg className="w-3 h-3 text-[#455566] group-hover/tip:text-[#7b8fa0] transition-colors flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <circle cx="12" cy="12" r="10" />
        <path d="M12 16v-4M12 8h.01" />
      </svg>
      <span className="invisible group-hover/tip:visible opacity-0 group-hover/tip:opacity-100 transition-all absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-1.5 bg-[#162028] border border-[#1e2d3a] rounded-lg text-[11px] text-[#7b8fa0] whitespace-nowrap z-50 shadow-lg max-w-xs">
        {text}
      </span>
    </span>
  );
}

// ── Section wrapper ──
function Section({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <div className={`bg-[#0f171e] border border-[rgba(14,165,233,0.08)] rounded-xl p-4 ${className}`}>
      {children}
    </div>
  );
}

// ── Section title ──
function SectionTitle({ children, tip, right }: { children: ReactNode; tip?: string; right?: ReactNode }) {
  return (
    <div className="flex items-center justify-between mb-3">
      {tip ? (
        <Tip text={tip}><h2 className="text-sm font-semibold text-[#e8edf2]">{children}</h2></Tip>
      ) : (
        <h2 className="text-sm font-semibold text-[#e8edf2]">{children}</h2>
      )}
      {right}
    </div>
  );
}

// ── Data row for firmography table ──
function Row({
  label,
  value,
  tip,
  mono,
  href,
  highlight,
  sub,
}: {
  label: string;
  value: string | null | undefined;
  tip?: string;
  mono?: boolean;
  href?: string;
  highlight?: "green" | "yellow" | "red" | "blue";
  sub?: string;
}) {
  if (!value) return null;
  const hc = highlight === "green" ? "text-[#22c55e]" : highlight === "yellow" ? "text-[#f59e0b]" : highlight === "red" ? "text-[#ef4444]" : highlight === "blue" ? "text-[#7dd3fc]" : "text-[#e8edf2]";

  return (
    <div className="flex items-baseline justify-between py-1.5 border-b border-[rgba(14,165,233,0.08)]/50 last:border-0 gap-3">
      <span className="text-xs text-[#455566] flex-shrink-0 w-36">
        {tip ? <Tip text={tip}>{label}</Tip> : label}
      </span>
      <span className={`text-sm text-right truncate ${mono ? "font-mono" : ""}`}>
        {href && value ? (
          <a href={href.startsWith("http") ? href : `https://${href}`} target="_blank" rel="noopener noreferrer" className="text-[#7dd3fc] hover:text-[#bae6fd] hover:underline transition-colors">
            {value}
          </a>
        ) : (
          <span className={hc}>
            {value || "—"}
          </span>
        )}
        {sub && <span className="text-[11px] text-[#455566] ml-1">{sub}</span>}
      </span>
    </div>
  );
}

// ── Badge ──
function Badge({ text, color = "slate" }: { text: string; color?: "emerald" | "blue" | "amber" | "red" | "purple" | "slate" }) {
  const cls: Record<string, string> = {
    emerald: "bg-[#22c55e]/10 text-[#22c55e] border-[#22c55e]/20",
    blue: "bg-[#0ea5e9]/10 text-[#7dd3fc] border-[#0ea5e9]/20",
    amber: "bg-[#f59e0b]/10 text-[#f59e0b] border-[#f59e0b]/20",
    red: "bg-[#ef4444]/10 text-[#ef4444] border-[#ef4444]/20",
    purple: "bg-[#a855f7]/10 text-[#a855f7] border-[#a855f7]/20",
    slate: "bg-[#455566]/10 text-[#7b8fa0] border-[#455566]/20",
  };
  return <span className={`inline-flex px-2 py-0.5 rounded-full text-[11px] font-medium border ${cls[color]}`}>{text}</span>;
}

// ── Quick link button ──
function QLink({ href, children }: { href: string; children: ReactNode }) {
  return (
    <a href={href} target="_blank" rel="noopener noreferrer"
      className="px-2.5 py-1.5 bg-[#162028] hover:bg-[rgba(14,165,233,0.08)] text-[#7b8fa0] hover:text-[#e8edf2] text-[11px] rounded-lg border border-[rgba(14,165,233,0.08)] transition-all">
      {children}
    </a>
  );
}

// ══════════════════════════════════════════
// ── Main page ──
// ══════════════════════════════════════════

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

  if (loading) return <div className="flex items-center justify-center h-64 text-[#455566]"><div className="w-6 h-6 border-2 border-[#0ea5e9] border-t-transparent rounded-full animate-spin mr-3" />Ladowanie danych firmy...</div>;
  if (!lead) return <div className="text-[#ef4444] p-8 text-center">Lead nie znaleziony</div>;

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

  // ══════════════════════════════════════════
  // ── Render ──
  // ══════════════════════════════════════════
  return (
    <div className="max-w-7xl mx-auto space-y-4">

      {/* ═══ HEADER BAR ═══ */}
      <div className="bg-[#0f171e] border border-[rgba(14,165,233,0.08)] rounded-xl p-4">
        <div className="flex items-start gap-3">
          <Link href="/leads" className="mt-1 p-1.5 rounded-lg hover:bg-[#162028] text-[#455566] hover:text-[#e8edf2] transition-all flex-shrink-0">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" /></svg>
          </Link>

          <div className="flex-1 min-w-0">
            {/* Company name + badges */}
            <div className="flex items-center gap-2 mb-1 flex-wrap">
              <h1 className="text-xl font-bold text-[#e8edf2] truncate">{lead.name}</h1>
              {lead.tier && <Badge text={`${lead.tier} — ${ti?.label}`} color={lead.tier === "S" ? "emerald" : lead.tier === "A" ? "blue" : lead.tier === "B" ? "amber" : "slate"} />}
              <Badge
                text={lead.vat_status || "VAT?"}
                color={lead.vat_status === "Czynny VAT" ? "emerald" : lead.vat_status === "Zwolniony" ? "amber" : "red"}
              />
            </div>
            {/* Identifiers row */}
            <div className="flex items-center gap-4 text-xs text-[#455566] flex-wrap">
              <Tip text="Numer Identyfikacji Podatkowej — kliknij aby sprawdzic w rejestr.io">
                <a href={`https://rejestr.io/krs?q=${lead.nip}`} target="_blank" rel="noopener noreferrer" className="font-mono text-[#7dd3fc] hover:text-[#bae6fd] hover:underline">
                  NIP {lead.nip}
                </a>
              </Tip>
              {(lead.regon || regon) && (
                <Tip text="Numer REGON — identyfikator w rejestrze GUS"><span className="font-mono">REGON {lead.regon || regon}</span></Tip>
              )}
              {(lead.krs || krsNum) && (
                <Tip text="Numer KRS — kliknij aby sprawdzic w rejestr.io">
                  <a href={`https://rejestr.io/krs/${lead.krs || krsNum}`} target="_blank" rel="noopener noreferrer" className="font-mono text-[#7dd3fc] hover:text-[#bae6fd] hover:underline">
                    KRS {lead.krs || krsNum}
                  </a>
                </Tip>
              )}
              {lead.city && <span>{lead.city}{lead.voivodeship ? `, woj. ${lead.voivodeship}` : ""}</span>}
            </div>
          </div>

          {/* Actions */}
          <div className="flex gap-2 flex-shrink-0">
            <button
              onClick={handleEnrichAndScore}
              disabled={enriching || scoring}
              className="px-4 py-2 bg-[#22c55e] hover:bg-[#4ade80] disabled:opacity-40 text-white text-xs rounded-lg font-semibold whitespace-nowrap glow-success transition-all"
            >
              {enriching ? "Pobieranie..." : scoring ? "Scoring..." : "Wzbogac + Score"}
            </button>
            <Link href={`/leads/${id}/edit`} className="px-3 py-2 bg-[#162028] hover:bg-[rgba(14,165,233,0.08)] text-[#7b8fa0] text-xs rounded-lg border border-[rgba(14,165,233,0.08)] transition-all">
              Edytuj
            </Link>
            <button onClick={handleDelete} className="px-3 py-2 bg-[#ef4444]/10 hover:bg-[#ef4444]/20 text-[#ef4444] text-xs rounded-lg border border-[#ef4444]/20 transition-all">
              Usun
            </button>
          </div>
        </div>
      </div>

      {/* ═══ MAIN LAYOUT: Left content (2/3) + Right sidebar (1/3) ═══ */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">

        {/* ────── LEFT COLUMN (2/3) ────── */}
        <div className="lg:col-span-2 space-y-4">

          {/* ── Firmography ── */}
          <Section>
            <SectionTitle tip="Dane firmowe zebrane z rejestrow: eKRS, GUS, CEIDG, Biala Lista VAT, strona WWW firmy">Dane firmowe</SectionTitle>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6">
              <div>
                <Row label="Pelna nazwa" value={lead.name} tip="Nazwa firmy z KRS/CEIDG/VAT" />
                <Row label="NIP" value={lead.nip} mono tip="Numer Identyfikacji Podatkowej" href={`https://rejestr.io/krs?q=${lead.nip}`} />
                <Row label="REGON" value={lead.regon || regon} mono tip="Numer REGON — identyfikator GUS" />
                <Row label="KRS" value={lead.krs || krsNum} mono tip="Krajowy Rejestr Sadowy" href={lead.krs || krsNum ? `https://rejestr.io/krs/${lead.krs || krsNum}` : undefined} />
                <Row label="Forma prawna" value={lead.legal_form || legalForm || gusLegalForm} tip="sp. z o.o., sp.k., sp.j., S.A., JDG itp." />
                <Row label="PKD (glowny)" value={lead.pkd ? `${lead.pkd} — ${lead.pkd_desc || ""}` : gusPkd ? `${gusPkd} — ${gusPkdDesc || ""}` : null} tip="Polska Klasyfikacja Dzialalnosci — branza firmy" />
                <Row label="Kategoria" value={lead.category} tip="Kategoria biznesowa leada" />
              </div>
              <div>
                <Row label="Adres" value={fullAddress || lead.city} tip="Kliknij aby otworzyc w Google Maps" href={fullAddress ? `https://www.google.com/maps/search/${encodeURIComponent(fullAddress)}` : undefined} />
                <Row label="Wojewodztwo" value={lead.voivodeship || gusVoivodeship} tip="Wojewodztwo wg rejestru GUS lub eKRS" />
                <Row label="Pracownicy" value={lead.employees != null ? `${lead.employees} os.` : null} tip="Szacunkowa liczba pracownikow" />
                <Row label="Przychod" value={lead.revenue_pln ? `${(lead.revenue_pln / 1_000_000).toFixed(1)}M PLN` : null} tip="Szacunkowy roczny przychod" sub={lead.revenue_band ? `(${lead.revenue_band})` : undefined} />
                <Row label="Lata dzialalnosci" value={lead.years_active != null ? `${lead.years_active.toFixed(1)} lat` : null} tip="Od daty rejestracji w KRS/CEIDG" />
                <Row label="Data rejestracji" value={regDate} tip="Data rejestracji w KRS lub rozpoczecia w CEIDG" />
                <Row label="Status VAT" value={lead.vat_status} highlight={lead.vat_status === "Czynny VAT" ? "green" : lead.vat_status === "Zwolniony" ? "yellow" : "red"} tip="Czynny VAT = aktywny podatnik" />
                <Row label="Strona WWW" value={lead.website} href={lead.website || undefined} tip="Strona internetowa firmy" />
              </div>
            </div>
          </Section>

          {/* ── Scoring Breakdown ── */}
          <Section>
            <SectionTitle
              tip="Scoring skladniowy: kazdy czynnik ma wage i wynik surowy (0-100). Suma wazona = koncowy score."
              right={
                <button onClick={handleScore} disabled={scoring} className="text-[11px] text-[#7dd3fc] hover:text-[#bae6fd] px-2.5 py-1 rounded-lg hover:bg-[#0ea5e9]/10 transition-all">
                  {scoring ? "Liczenie..." : "Przelicz"}
                </button>
              }
            >
              Scoring — rozklad
            </SectionTitle>
            {scoringResult?.breakdown ? (
              <div className="space-y-2.5">
                {scoringResult.breakdown.map((b) => {
                  const tips: Record<string, string> = {
                    employees: "Pracownicy: <=9=20, <=49=55, <=249=78, >249=92",
                    revenueBand: "Przychody: micro=25, small=55, medium=75, large=92",
                    yearsActive: "Lata: <=1=20, <=3=40, <=7=60, <=12=75, >12=88",
                    vatStatus: "Czynny=80, Zwolniony=55, Niepewny=35",
                    pkdFit: "Dopasowanie PKD do budownictwa + korekta rozmiaru",
                    basketSignal: "Sygnal koszykowy: 30+(min(1,koszyk/8000)^0.65)*60",
                    locality: "Duze miasto=75, inne=55",
                  };
                  return (
                    <div key={b.factor}>
                      <div className="flex justify-between text-xs mb-1">
                        <Tip text={tips[b.factor] || b.factor}>
                          <span className="text-[#7b8fa0]">{b.label}</span>
                        </Tip>
                        <span className="text-[#455566] tabular-nums">
                          <span className="text-[#e8edf2] font-semibold">{b.raw_score}</span>/100 x {(b.weight * 100).toFixed(0)}% = <span className="text-[#e8edf2] font-semibold">{b.weighted_score.toFixed(1)}</span>
                        </span>
                      </div>
                      <div className="h-2 bg-[#162028] rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all duration-700 ${b.raw_score >= 70 ? "bg-[#22c55e]" : b.raw_score >= 50 ? "bg-[#0ea5e9]" : b.raw_score >= 30 ? "bg-[#f59e0b]" : "bg-[#ef4444]"}`}
                          style={{ width: `${b.raw_score}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
                <div className="border-t border-[rgba(14,165,233,0.08)] pt-2 mt-3 flex justify-between items-center">
                  <span className="text-xs text-[#455566]">Suma wazona</span>
                  <span className="text-[#e8edf2] font-black text-lg">{lead.score ?? "—"}<span className="text-[#455566] text-xs font-normal"> / 100</span></span>
                </div>
              </div>
            ) : (
              <div className="text-center py-8">
                <p className="text-[#455566] text-sm mb-2">Kliknij aby obliczyc scoring</p>
                <button onClick={handleScore} disabled={scoring} className="px-4 py-2 bg-[#0ea5e9] hover:bg-[#38bdf8] text-white text-xs rounded-lg transition-all">
                  Przelicz scoring
                </button>
              </div>
            )}
          </Section>

          {/* ── Board / People ── */}
          <Section>
            <SectionTitle tip="Czlonkowie zarzadu, rady nadzorczej i wspolnicy ze zrodel: eKRS, VAT">Zarzad i reprezentacja</SectionTitle>

            {board.length > 0 ? (
              <div>
                <p className="text-[10px] text-[#455566] mb-2 uppercase tracking-wider">{boardOrganName}</p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  {board.map((m, i) => (
                    <div key={i} className="flex items-center justify-between p-2 bg-[#162028] rounded-lg">
                      <div className="flex items-center gap-2 min-w-0">
                        <div className="w-7 h-7 rounded-full flex items-center justify-center text-[10px] font-bold flex-shrink-0 bg-[#0ea5e9]/20 text-[#7dd3fc]">
                          {m.name.split(" ").map(n => n[0]).join("").slice(0, 2).toUpperCase()}
                        </div>
                        <div className="min-w-0">
                          <span className="text-xs block truncate text-[#e8edf2]">
                            {m.name}
                          </span>
                          <span className="text-[10px] text-[#455566]">{m.function || "Czlonek"}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <p className="text-[#455566] text-xs py-3 text-center">Brak danych — kliknij &quot;Wzbogac + Score&quot;</p>
            )}

            {/* Supervisory Board */}
            {supervisory.length > 0 && (
              <div className="mt-3 pt-3 border-t border-[rgba(14,165,233,0.08)]">
                <Tip text="Rada Nadzorcza — organ nadzoru spolki, dane z eKRS">
                  <p className="text-[10px] text-[#455566] mb-2 uppercase tracking-wider">Rada Nadzorcza ({supervisory.length})</p>
                </Tip>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-1.5">
                  {supervisory.map((m, i) => (
                    <div key={i} className="flex items-center justify-between p-1.5 bg-[#162028] rounded-lg text-xs">
                      <span className="text-[#e8edf2]">{m.name}</span>
                      <span className="text-[#455566] text-[10px]">{m.function}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Shareholders */}
            {shareholders.length > 0 && (
              <div className="mt-3 pt-3 border-t border-[rgba(14,165,233,0.08)]">
                <Tip text="Wspolnicy/udzialowcy spolki — dane z eKRS">
                  <p className="text-[10px] text-[#455566] mb-2 uppercase tracking-wider">Wspolnicy ({shareholders.length})</p>
                </Tip>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-1.5">
                  {shareholders.map((s, i) => (
                    <div key={i} className="p-1.5 bg-[#162028] rounded-lg text-xs">
                      <span className="text-[#e8edf2]">{s.name}</span>
                      {s.shares && <span className="text-[#455566] text-[10px] ml-2">{s.shares}</span>}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {shareCapital && (
              <div className="mt-3 pt-3 border-t border-[rgba(14,165,233,0.08)] flex items-center gap-2">
                <Tip text="Kapital zakladowy spolki"><span className="text-[10px] text-[#455566]">Kapital zakladowy:</span></Tip>
                <span className="text-xs text-[#e8edf2] font-medium">{shareCapital}</span>
              </div>
            )}
          </Section>

          {/* ── PKD codes (if many) ── */}
          {pkdAll.length > 1 && (
            <Section>
              <SectionTitle tip="Polska Klasyfikacja Dzialalnosci — lista kodow PKD z KRS">Kody PKD ({pkdAll.length})</SectionTitle>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-1">
                {pkdAll.map((p, i) => (
                  <a key={i}
                    href={`https://www.biznes.gov.pl/pl/tabela-pkd/pkd/${p.code.replace(".", "")}`}
                    target="_blank" rel="noopener noreferrer"
                    className={`flex gap-2 text-xs p-2 rounded-lg hover:bg-[#162028] transition-all ${i === 0 ? "bg-[#0ea5e9]/5 border border-[#0ea5e9]/20" : ""}`}
                  >
                    <span className="font-mono text-[#7dd3fc] flex-shrink-0 w-12">{p.code}</span>
                    <span className="text-[#7b8fa0] flex-1 truncate">{p.desc || "—"}</span>
                    {i === 0 && <Badge text="glowny" color="blue" />}
                  </a>
                ))}
              </div>
            </Section>
          )}

          {/* ── Description ── */}
          {lead.description && (
            <Section>
              <SectionTitle tip="Opis firmy z rejestrow, strony WWW, Google i portali">Opis firmy</SectionTitle>
              <p className="text-xs text-[#7b8fa0] whitespace-pre-wrap leading-relaxed">{lead.description}</p>
            </Section>
          )}

          {/* ── Map ── */}
          {lead.latitude && lead.longitude && (
            <div className="bg-[#0f171e] border border-[rgba(14,165,233,0.08)] rounded-xl p-1.5 h-[280px]">
              <LeadMap latitude={lead.latitude} longitude={lead.longitude} name={lead.name} address={fullAddress} />
            </div>
          )}

          {/* ── Notes + History row ── */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Notes */}
            <Section>
              <SectionTitle tip="Twoje notatki do tego leada" right={
                !editingNotes ? (
                  <button onClick={() => setEditingNotes(true)} className="text-[11px] text-[#7dd3fc] hover:text-[#bae6fd] px-2 py-1 rounded-lg hover:bg-[#0ea5e9]/10 transition-all">
                    Edytuj
                  </button>
                ) : undefined
              }>
                Notatki
              </SectionTitle>
              {editingNotes ? (
                <div>
                  <textarea
                    value={notesValue}
                    onChange={(e) => setNotesValue(e.target.value)}
                    rows={5}
                    className="w-full px-3 py-2 bg-[#020709] border border-[rgba(14,165,233,0.08)] rounded-lg text-[#e8edf2] text-xs focus:ring-2 focus:ring-[#0ea5e9]/50 focus:outline-none resize-none placeholder-[#455566]"
                    placeholder="Dodaj notatki..."
                  />
                  <div className="flex gap-2 mt-2">
                    <button onClick={saveNotes} className="px-3 py-1.5 bg-[#22c55e] hover:bg-[#4ade80] text-white text-[11px] rounded-lg transition-all">Zapisz</button>
                    <button onClick={() => { setEditingNotes(false); setNotesValue(lead.notes || ""); }} className="px-3 py-1.5 bg-[#162028] hover:bg-[rgba(14,165,233,0.08)] text-[#7b8fa0] text-[11px] rounded-lg transition-all">Anuluj</button>
                  </div>
                </div>
              ) : (
                <p className="text-[#7b8fa0] text-xs whitespace-pre-wrap">{lead.notes || "Brak notatek."}</p>
              )}
              {lead.ai_summary && (
                <div className="mt-3 pt-3 border-t border-[rgba(14,165,233,0.08)]">
                  <Tip text="Podsumowanie AI"><p className="text-[10px] text-[#a855f7] font-medium mb-1">AI Summary</p></Tip>
                  <p className="text-xs text-[#7b8fa0]">{lead.ai_summary}</p>
                </div>
              )}
            </Section>

            {/* History */}
            <Section>
              <SectionTitle tip="Historia przeliczen scoringu — zmiany w czasie">Historia scoringu ({history.length})</SectionTitle>
              {history.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="text-[#455566] border-b border-[rgba(14,165,233,0.08)]">
                        <th className="text-left py-1.5 pr-3 font-medium text-[10px] uppercase">Data</th>
                        <th className="text-center py-1.5 px-2 font-medium text-[10px] uppercase">Score</th>
                        <th className="text-center py-1.5 px-2 font-medium text-[10px] uppercase">Tier</th>
                        <th className="text-right py-1.5 pl-2 font-medium text-[10px] uppercase">Potencjal</th>
                      </tr>
                    </thead>
                    <tbody>
                      {history.map((h, i) => (
                        <tr key={h.id} className={`border-b border-[rgba(14,165,233,0.08)]/50 ${i === 0 ? "bg-[#162028]/50" : ""}`}>
                          <td className="py-1.5 pr-3 text-[#455566] text-[11px]">
                            {new Date(h.scored_at).toLocaleString("pl-PL", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}
                          </td>
                          <td className="py-1.5 px-2 text-center text-[#e8edf2] font-bold">{h.score}</td>
                          <td className="py-1.5 px-2 text-center">
                            <Badge text={h.tier} color={h.tier === "S" ? "emerald" : h.tier === "A" ? "blue" : h.tier === "B" ? "amber" : "slate"} />
                          </td>
                          <td className="py-1.5 pl-2 text-right text-[#455566]">{(h.annual_potential / 1000).toFixed(0)}k</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="text-[#455566] text-xs text-center py-6">Brak historii — przelicz scoring</p>
              )}
            </Section>
          </div>
        </div>

        {/* ────── RIGHT SIDEBAR (1/3) ────── */}
        <div className="space-y-4">

          {/* ── Score Card ── */}
          <Section className={ti ? `border ${ti.border}` : ""}>
            <div className="flex flex-col items-center">
              <Tip text="Scoring 0-100: pracownicy, przychody, lata, VAT, PKD, koszyk, lokalizacja">
                <span className="text-[10px] text-[#455566] uppercase tracking-wider mb-2">Score</span>
              </Tip>
              <div className="relative w-28 h-28 mb-2">
                <svg className="w-28 h-28 -rotate-90" viewBox="0 0 120 120">
                  <circle cx="60" cy="60" r="54" fill="none" stroke="rgba(14,165,233,0.08)" strokeWidth="8" />
                  <circle cx="60" cy="60" r="54" fill="none" stroke={ti?.ring || "#455566"} strokeWidth="8" strokeLinecap="round"
                    strokeDasharray={circ} strokeDashoffset={dashOff} className="transition-all duration-1000 ease-out" />
                </svg>
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                  <span className={`text-3xl font-black ${ti?.color || "text-[#455566]"}`}>{lead.score ?? "—"}</span>
                  <span className="text-[10px] text-[#455566]">/100</span>
                </div>
              </div>
              {lead.tier && <Badge text={`Tier ${lead.tier} — ${ti?.label}`} color={lead.tier === "S" ? "emerald" : lead.tier === "A" ? "blue" : lead.tier === "B" ? "amber" : "slate"} />}
            </div>

            {/* Potential + revenue */}
            <div className="mt-4 pt-3 border-t border-[rgba(14,165,233,0.08)] text-center">
              <Tip text="Roczny potencjal = ARPU 18k x mnoznik tier (S:30x, A:12x, B:5x, C:2x)">
                <p className="text-[10px] text-[#455566] uppercase mb-1">Potencjal roczny</p>
              </Tip>
              <p className="text-2xl font-black text-[#e8edf2]">
                {lead.annual_potential ? `${(lead.annual_potential / 1000).toFixed(0)}k` : "—"}
                <span className="text-sm font-normal text-[#455566] ml-1">PLN</span>
              </p>
              {lead.revenue_band && (
                <p className="text-[11px] text-[#455566] mt-1">{REV_BAND[lead.revenue_band] || lead.revenue_band}</p>
              )}
            </div>

            {/* Recommended action */}
            {ti && (
              <div className="mt-3 pt-3 border-t border-[rgba(14,165,233,0.08)]">
                <Tip text="Rekomendacja handlowa na podstawie tier scoringowego">
                  <p className="text-[10px] text-[#455566] uppercase mb-1">Rekomendacja</p>
                </Tip>
                <p className={`text-xs font-medium ${ti.color} leading-snug`}>{ti.action}</p>
              </div>
            )}

            {/* Categories */}
            {scoringResult?.categories && scoringResult.categories.length > 0 && (
              <div className="mt-3 pt-3 border-t border-[rgba(14,165,233,0.08)]">
                <Tip text="Kategorie produktow budowlanych dopasowane na podstawie PKD">
                  <p className="text-[10px] text-[#455566] uppercase mb-1.5">Kategorie</p>
                </Tip>
                <div className="flex flex-wrap gap-1">
                  {scoringResult.categories.map((c, i) => (
                    <Badge key={i} text={c} color="blue" />
                  ))}
                </div>
              </div>
            )}
          </Section>

          {/* ── Contact ── */}
          <Section>
            <SectionTitle tip="Dane kontaktowe ze strony WWW, Panorama Firm, Aleo i rejestrow">Kontakt</SectionTitle>
            <div className="space-y-2.5">
              {lead.contact_person && (
                <div>
                  <span className="text-[10px] text-[#455566] block mb-0.5">Osoba kontaktowa</span>
                  <span className="text-xs text-[#e8edf2]">{lead.contact_person}</span>
                </div>
              )}
              {lead.contact_phone && (
                <div>
                  <span className="text-[10px] text-[#455566] block mb-0.5">
                    <Tip text="Kliknij aby zadzwonic">Telefon</Tip>
                  </span>
                  <a href={`tel:${lead.contact_phone}`} className="text-xs text-[#7dd3fc] hover:text-[#bae6fd] hover:underline flex items-center gap-1.5">
                    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" /></svg>
                    {lead.contact_phone}
                  </a>
                </div>
              )}
              {lead.contact_email && (
                <div>
                  <span className="text-[10px] text-[#455566] block mb-0.5">
                    <Tip text="Kliknij aby wyslac email">Email</Tip>
                  </span>
                  <a href={`mailto:${lead.contact_email}`} className="text-xs text-[#7dd3fc] hover:text-[#bae6fd] hover:underline flex items-center gap-1.5">
                    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" /></svg>
                    {lead.contact_email}
                  </a>
                </div>
              )}
              {lead.website && (
                <div>
                  <span className="text-[10px] text-[#455566] block mb-0.5">
                    <Tip text="Strona internetowa firmy">WWW</Tip>
                  </span>
                  <a href={lead.website.startsWith("http") ? lead.website : `https://${lead.website}`} target="_blank" rel="noopener noreferrer" className="text-xs text-[#7dd3fc] hover:text-[#bae6fd] hover:underline truncate block">
                    {lead.website}
                  </a>
                </div>
              )}
              {fullAddress && (
                <div>
                  <span className="text-[10px] text-[#455566] block mb-0.5">
                    <Tip text="Kliknij aby otworzyc w Google Maps">Adres</Tip>
                  </span>
                  <a href={`https://www.google.com/maps/search/${encodeURIComponent(fullAddress)}`} target="_blank" rel="noopener noreferrer" className="text-xs text-[#7dd3fc] hover:text-[#bae6fd] hover:underline">
                    {fullAddress}
                  </a>
                </div>
              )}
              {(residenceAddress || workingAddress) && (
                <div className="pt-2 border-t border-[rgba(14,165,233,0.08)] space-y-2">
                  {residenceAddress && (
                    <div>
                      <span className="text-[10px] text-[#455566] block mb-0.5">Adres siedziby (VAT)</span>
                      <a href={`https://www.google.com/maps/search/${encodeURIComponent(residenceAddress)}`} target="_blank" rel="noopener noreferrer" className="text-xs text-[#7dd3fc] hover:text-[#bae6fd] hover:underline">
                        {residenceAddress}
                      </a>
                    </div>
                  )}
                  {workingAddress && workingAddress !== residenceAddress && (
                    <div>
                      <span className="text-[10px] text-[#455566] block mb-0.5">Adres dzialalnosci</span>
                      <a href={`https://www.google.com/maps/search/${encodeURIComponent(workingAddress)}`} target="_blank" rel="noopener noreferrer" className="text-xs text-[#7dd3fc] hover:text-[#bae6fd] hover:underline">
                        {workingAddress}
                      </a>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Social Media */}
            {lead.social_media && Object.keys(lead.social_media).length > 0 && (
              <div className="mt-3 pt-3 border-t border-[rgba(14,165,233,0.08)]">
                <p className="text-[10px] text-[#455566] mb-1.5 uppercase">Social Media</p>
                <div className="flex flex-wrap gap-1.5">
                  {Object.entries(lead.social_media).map(([platform, url]) => (
                    <a key={platform} href={url} target="_blank" rel="noopener noreferrer"
                      className="px-2 py-1 bg-[#0ea5e9]/10 hover:bg-[#0ea5e9]/20 text-[#7dd3fc] text-[10px] rounded-lg border border-[#0ea5e9]/20 transition-all capitalize">
                      {platform}
                    </a>
                  ))}
                </div>
              </div>
            )}

            {/* Bank accounts */}
            {bankAccounts.length > 0 && (
              <div className="mt-3 pt-3 border-t border-[rgba(14,165,233,0.08)]">
                <Tip text="Konta bankowe z Bialej Listy VAT — zweryfikowane przez MF">
                  <p className="text-[10px] text-[#455566] mb-1.5 uppercase">Konta bankowe ({bankAccounts.length})</p>
                </Tip>
                <div className="space-y-1 max-h-20 overflow-y-auto">
                  {bankAccounts.map((acc, i) => (
                    <p key={i} className="text-[10px] font-mono text-[#455566] bg-[#162028] p-1 rounded">{String(acc)}</p>
                  ))}
                </div>
              </div>
            )}
          </Section>

          {/* ── OSINT Sources ── */}
          <Section>
            <SectionTitle tip="Rejestry uzyte do wzbogacenia — zielony=OK, zolty=blad, szary=brak">Zrodla OSINT</SectionTitle>
            <div className="space-y-1.5">
              {(["vat_whitelist", "ekrs", "ceidg", "gus"] as const).map((src) => {
                const raw = lead.osint_raw?.[src] as Record<string, unknown> | undefined;
                const hasData = lead.sources?.includes(src);
                const hasError = raw && "error" in raw;
                const errStr = raw ? String(raw.error) : "";
                const isCeidgNA = src === "ceidg" && (errStr === "not_found" || errStr === "not_applicable");
                const srcInfo = SRC_LABEL[src];
                return (
                  <Tip key={src} text={srcInfo.tip}>
                    <div className={`flex items-center gap-2 p-2 rounded-lg cursor-help w-full ${hasData ? "bg-[#22c55e]/5 border border-[#22c55e]/20" : hasError && !isCeidgNA ? "bg-[#f59e0b]/5 border border-[#f59e0b]/20" : "bg-[#162028] border border-[rgba(14,165,233,0.08)]"}`}>
                      <div className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${hasData ? "bg-[#22c55e] pulse-dot" : isCeidgNA ? "bg-[#455566]" : hasError ? "bg-[#f59e0b]" : "bg-[#455566]"}`} />
                      <span className={`text-xs flex-1 ${hasData ? "text-[#22c55e]" : "text-[#455566]"}`}>{srcInfo.name}</span>
                      <span className={`text-[10px] ${hasData ? "text-[#22c55e]" : isCeidgNA ? "text-[#455566]" : hasError ? "text-[#f59e0b]" : "text-[#1e2d3a]"}`}>
                        {hasData ? "OK" : isCeidgNA ? "N/D" : hasError ? "Blad" : "—"}
                      </span>
                    </div>
                  </Tip>
                );
              })}
            </div>
            <button onClick={() => setShowOsintRaw(!showOsintRaw)} className="mt-2 text-[10px] text-[#455566] hover:text-[#7b8fa0] transition-colors">
              {showOsintRaw ? "Ukryj JSON" : "Pokaz JSON"}
            </button>
            {showOsintRaw && lead.osint_raw && (
              <pre className="mt-2 p-2 bg-[#020709] rounded-lg text-[10px] text-[#455566] overflow-x-auto max-h-40 overflow-y-auto border border-[rgba(14,165,233,0.08)]">
                {JSON.stringify(lead.osint_raw, null, 2)}
              </pre>
            )}
          </Section>

          {/* ── Quick Actions ── */}
          <Section>
            <SectionTitle tip="Szybkie linki do rejestrow i narzedzi">Szybkie akcje</SectionTitle>
            <div className="flex flex-wrap gap-1.5">
              <button onClick={handleEnrich} disabled={enriching} className="px-2.5 py-1.5 bg-[#a855f7]/10 hover:bg-[#a855f7]/20 text-[#a855f7] text-[11px] rounded-lg border border-[#a855f7]/20 transition-all">
                {enriching ? "Trwa..." : "Tylko OSINT"}
              </button>
              <button onClick={handleScore} disabled={scoring} className="px-2.5 py-1.5 bg-[#0ea5e9]/10 hover:bg-[#0ea5e9]/20 text-[#7dd3fc] text-[11px] rounded-lg border border-[#0ea5e9]/20 transition-all">
                {scoring ? "Trwa..." : "Tylko Scoring"}
              </button>
              {lead.website && <QLink href={lead.website.startsWith("http") ? lead.website : `https://${lead.website}`}>WWW</QLink>}
              <QLink href={`https://www.google.com/search?q=${encodeURIComponent(lead.name + " " + (lead.city || ""))}`}>Google</QLink>
              <QLink href={`https://rejestr.io/krs?q=${encodeURIComponent(lead.nip || lead.name)}`}>Rejestr.io</QLink>
              <QLink href={`https://panoramafirm.pl/szukaj?k=${encodeURIComponent(lead.name)}`}>Panorama</QLink>
              <QLink href={`https://aleo.com/pl/szukaj?query=${encodeURIComponent(lead.nip || lead.name)}`}>Aleo</QLink>
            </div>
          </Section>
        </div>
      </div>

      {/* AI Chat */}
      <AiChat leadId={lead.id} leadName={lead.name} />
    </div>
  );
}
