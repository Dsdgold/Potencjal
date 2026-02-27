"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { companiesApi } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { formatPLN, formatNIP, riskBandColor, riskBandLabel, cn } from "@/lib/utils";

export default function CompanyProfilePage() {
  const { nip } = useParams<{ nip: string }>();
  const { token } = useAuth();
  const router = useRouter();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [tab, setTab] = useState("overview");
  const [noteText, setNoteText] = useState("");

  useEffect(() => {
    if (!token || !nip) return;
    setLoading(true);
    companiesApi.lookup(nip as string, token)
      .then(setData)
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, [nip, token]);

  if (loading) return (
    <div className="flex items-center justify-center py-20">
      <div className="w-8 h-8 border-3 border-sig-border border-t-sig-red rounded-full animate-spin" />
    </div>
  );

  if (error) return (
    <div className="bg-red-500/10 border border-red-500/30 rounded-2xl p-6 text-center">
      <p className="text-red-400">{error}</p>
      <button onClick={() => router.push("/dashboard")} className="mt-4 text-sm text-sig-red hover:underline">
        Wróć do dashboard
      </button>
    </div>
  );

  if (!data) return null;

  const { company, snapshot, score, materials, sources, quality } = data;
  const s = snapshot || {};
  const sc = score || {};
  const comps = sc.components || [];

  const tabs = [
    { id: "overview", label: "Przegląd" },
    { id: "scoring", label: "Scoring & Ryzyko" },
    s.pkd_codes?.length && { id: "materials", label: "Materiały" },
    { id: "registers", label: "Rejestry" },
    { id: "notes", label: "Notatki" },
  ].filter(Boolean);

  return (
    <div className="space-y-4 animate-fade-in">
      {/* Back button */}
      <button onClick={() => router.push("/dashboard")} className="text-sm text-sig-muted hover:text-white transition">
        ← Dashboard
      </button>

      {/* Company header */}
      <div className="bg-sig-card border border-sig-border rounded-2xl p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <h1 className="text-2xl font-black leading-tight">{company?.name || s.name || "—"}</h1>
            <p className="text-sig-muted mt-1">{s.business_address || s.registered_address || ""}</p>
            <div className="flex flex-wrap gap-2 mt-3">
              <span className="text-xs px-2 py-1 rounded-lg bg-sig-surface border border-sig-border">
                NIP: {formatNIP(nip as string)}
              </span>
              {s.regon && <span className="text-xs px-2 py-1 rounded-lg bg-sig-surface border border-sig-border">REGON: {s.regon}</span>}
              {s.krs && <span className="text-xs px-2 py-1 rounded-lg bg-sig-surface border border-sig-border">KRS: {s.krs}</span>}
              {s.legal_form && <span className="text-xs px-2 py-1 rounded-lg bg-sig-surface border border-sig-border">{s.legal_form}</span>}
            </div>
          </div>
          <div className="flex gap-2">
            {s.vat_status === "Czynny" ? (
              <span className="px-3 py-1.5 rounded-lg bg-green-500/10 text-green-400 border border-green-500/20 text-sm font-bold">
                VAT Czynny
              </span>
            ) : (
              <span className="px-3 py-1.5 rounded-lg bg-red-500/10 text-red-400 border border-red-500/20 text-sm font-bold">
                VAT: {s.vat_status || "Brak danych"}
              </span>
            )}
          </div>
        </div>

        {/* Data quality indicator */}
        {quality && (
          <div className="mt-4 flex gap-4 text-xs text-sig-muted">
            <span>Kompletność: {quality.completeness_pct}%</span>
            <span>Źródeł: {quality.sources_count}</span>
            <span>Pewność: {quality.confidence}</span>
          </div>
        )}
      </div>

      {/* KPI Cards */}
      {sc.score_0_100 != null && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Score */}
          <div className="bg-sig-card border border-sig-border rounded-2xl p-5 text-center">
            <div className="text-xs text-sig-muted mb-2">Scoring ryzyka</div>
            <div className="relative mx-auto w-32 h-16 mb-2">
              <svg viewBox="0 0 200 100" className="w-full">
                <path d="M10,95 A85,85 0 0,1 190,95" fill="none" stroke="#252540" strokeWidth="14" strokeLinecap="round"/>
                <path d="M10,95 A85,85 0 0,1 190,95" fill="none"
                  stroke={riskBandColor(sc.risk_band)}
                  strokeWidth="14" strokeLinecap="round"
                  strokeDasharray={`${(sc.score_0_100 / 100) * 267} 267`}
                  style={{ transition: "stroke-dasharray 1s ease" }}
                />
              </svg>
              <div className="absolute inset-0 flex items-end justify-center pb-0">
                <span className="text-3xl font-black" style={{ color: riskBandColor(sc.risk_band) }}>
                  {sc.score_0_100}
                </span>
              </div>
            </div>
            <div className="text-sm font-bold" style={{ color: riskBandColor(sc.risk_band) }}>
              Pasmo {sc.risk_band} — {riskBandLabel(sc.risk_band)}
            </div>
          </div>

          {/* Credit Limit */}
          <div className="bg-sig-card border border-sig-border rounded-2xl p-5 text-center">
            <div className="text-xs text-sig-muted mb-2">Sugerowany limit kredytowy</div>
            <div className="text-3xl font-black text-sig-text">
              {sc.credit_limit_suggested > 0 ? formatPLN(sc.credit_limit_suggested) : "Przedpłata"}
            </div>
            {sc.credit_limit_min > 0 && (
              <div className="text-xs text-sig-muted mt-1">
                Zakres: {formatPLN(sc.credit_limit_min)} – {formatPLN(sc.credit_limit_max)}
              </div>
            )}
            <div className="flex justify-center gap-4 mt-3 text-xs">
              {sc.payment_terms_days > 0 && (
                <span className="px-2 py-1 rounded bg-sig-surface border border-sig-border">
                  {sc.payment_terms_days} dni
                </span>
              )}
              {sc.discount_pct > 0 && (
                <span className="px-2 py-1 rounded bg-green-500/10 text-green-400 border border-green-500/20">
                  Rabat {sc.discount_pct}%
                </span>
              )}
            </div>
          </div>

          {/* Materiały top 3 */}
          <div className="bg-sig-card border border-sig-border rounded-2xl p-5">
            <div className="text-xs text-sig-muted mb-2 text-center">Potencjał materiałowy</div>
            {materials?.categories?.slice(0, 4).map((cat: any) => (
              <div key={cat.code} className="flex items-center gap-2 mb-2">
                <div className="flex-1">
                  <div className="text-xs font-semibold">{cat.name_pl}</div>
                  <div className="h-1.5 bg-sig-surface rounded-full mt-0.5 overflow-hidden">
                    <div className="h-full rounded-full bg-sig-red" style={{ width: `${cat.confidence * 100}%`, transition: "width 0.5s" }} />
                  </div>
                </div>
                <span className="text-xs text-sig-muted w-8 text-right">{Math.round(cat.confidence * 100)}%</span>
              </div>
            ))}
            {(!materials?.categories?.length) && <p className="text-xs text-sig-muted text-center">Brak danych</p>}
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 border-b border-sig-border pb-0 no-print overflow-x-auto">
        {tabs.map((t: any) => (
          <button key={t.id} onClick={() => setTab(t.id)}
            className={cn("px-4 py-2 text-sm font-medium rounded-t-lg transition whitespace-nowrap",
              tab === t.id ? "bg-sig-card border border-sig-border border-b-sig-card text-sig-red" : "text-sig-muted hover:text-white"
            )}>
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="animate-fade-in">
        {tab === "overview" && <OverviewTab snapshot={s} score={sc} />}
        {tab === "scoring" && <ScoringTab score={sc} />}
        {tab === "materials" && <MaterialsTab materials={materials} />}
        {tab === "registers" && <RegistersTab snapshot={s} sources={sources} nip={nip as string} />}
        {tab === "notes" && <NotesTab nip={nip as string} token={token!} />}
      </div>
    </div>
  );
}

function OverviewTab({ snapshot: s, score: sc }: { snapshot: any; score: any }) {
  const rows = [
    s.name && ["Nazwa", s.name],
    s.legal_form && ["Forma prawna", s.legal_form],
    s.nip && ["NIP", formatNIP(s.nip)],
    s.regon && ["REGON", s.regon],
    s.krs && ["KRS", s.krs],
    s.vat_status && ["Status VAT", s.vat_status],
    s.registered_address && ["Adres rejestrowy", s.registered_address],
    s.business_address && s.business_address !== s.registered_address && ["Adres działalności", s.business_address],
    s.city && ["Miasto", s.city],
    s.registration_date && ["Data rejestracji", s.registration_date],
    s.share_capital && ["Kapitał zakładowy", `${Number(s.share_capital).toLocaleString("pl-PL")} ${s.share_capital_currency || "PLN"}`],
    s.employee_count_range && ["Zatrudnienie", s.employee_count_range],
    s.pkd_main_code && ["PKD główne", `${s.pkd_main_code} — ${s.pkd_main_name || ""}`],
    s.bank_account_count != null && ["Rachunki na Białej Liście", `${s.bank_account_count} szt.`],
    s.website && ["Strona www", s.website],
    s.email && ["Email", s.email],
    s.phone && ["Telefon", s.phone],
  ].filter(Boolean);

  return (
    <div className="grid md:grid-cols-2 gap-4">
      <div className="bg-sig-card border border-sig-border rounded-2xl p-5">
        <h3 className="text-sm font-bold text-sig-red mb-3">Dane podstawowe</h3>
        <table className="w-full text-sm">
          <tbody>
            {rows.map((row: any, i: number) => (
              <tr key={i} className="border-b border-sig-border/50 last:border-0">
                <td className="py-2 text-sig-muted w-40">{row[0]}</td>
                <td className="py-2 font-medium">{row[1]}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Flags */}
      <div className="space-y-4">
        {sc.green_flags?.length > 0 && (
          <div className="bg-sig-card border border-sig-border rounded-2xl p-5">
            <h3 className="text-sm font-bold text-green-400 mb-3">Atuty</h3>
            <ul className="space-y-1">
              {sc.green_flags.map((f: string, i: number) => (
                <li key={i} className="text-sm flex gap-2"><span className="text-green-400">✓</span> {f}</li>
              ))}
            </ul>
          </div>
        )}
        {sc.red_flags?.length > 0 && (
          <div className="bg-sig-card border border-sig-border rounded-2xl p-5">
            <h3 className="text-sm font-bold text-red-400 mb-3">Czynniki ryzyka</h3>
            <ul className="space-y-1">
              {sc.red_flags.map((f: string, i: number) => (
                <li key={i} className="text-sm flex gap-2"><span className="text-red-400">✗</span> {f}</li>
              ))}
            </ul>
          </div>
        )}
        {/* Representatives */}
        {s.representatives?.length > 0 && (
          <div className="bg-sig-card border border-sig-border rounded-2xl p-5">
            <h3 className="text-sm font-bold text-sig-red mb-3">Zarząd</h3>
            {s.representatives.map((r: any, i: number) => (
              <div key={i} className="text-sm py-1 flex justify-between">
                <span>{r.name}</span>
                <span className="text-sig-muted">{r.function || ""}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function ScoringTab({ score: sc }: { score: any }) {
  const comps = sc.components || [];
  return (
    <div className="space-y-4">
      <div className="bg-sig-card border border-sig-border rounded-2xl p-5">
        <h3 className="text-sm font-bold text-sig-red mb-1">Podsumowanie</h3>
        <p className="text-sm text-sig-muted">{sc.explanation_summary}</p>
        {sc.explanation && <p className="text-sm text-sig-muted mt-2">{sc.explanation}</p>}
      </div>

      <div className="bg-sig-card border border-sig-border rounded-2xl p-5">
        <h3 className="text-sm font-bold text-sig-red mb-4">Komponenty scoringu ({comps.length})</h3>
        <div className="space-y-3">
          {comps.map((c: any) => (
            <div key={c.name}>
              <div className="flex justify-between text-sm mb-1">
                <span className="font-medium">{c.label_pl}</span>
                <span className="text-sig-muted">{c.points}/{c.max_points} pkt</span>
              </div>
              <div className="h-2 bg-sig-surface rounded-full overflow-hidden">
                <div className="h-full rounded-full transition-all duration-500"
                  style={{
                    width: `${(c.points / c.max_points) * 100}%`,
                    backgroundColor: c.points / c.max_points >= 0.7 ? "#22c55e" : c.points / c.max_points >= 0.4 ? "#f59e0b" : "#ef4444"
                  }} />
              </div>
              <p className="text-xs text-sig-muted mt-0.5">{c.explanation}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Credit explanation */}
      <div className="bg-sig-card border border-sig-border rounded-2xl p-5">
        <h3 className="text-sm font-bold text-sig-red mb-2">Limit kredytowy — uzasadnienie</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
          <div className="text-center p-3 bg-sig-surface rounded-xl">
            <div className="text-lg font-bold">{sc.credit_limit_suggested > 0 ? formatPLN(sc.credit_limit_suggested) : "Przedpłata"}</div>
            <div className="text-xs text-sig-muted">Sugerowany</div>
          </div>
          <div className="text-center p-3 bg-sig-surface rounded-xl">
            <div className="text-lg font-bold">{formatPLN(sc.credit_limit_min || 0)}</div>
            <div className="text-xs text-sig-muted">Minimum</div>
          </div>
          <div className="text-center p-3 bg-sig-surface rounded-xl">
            <div className="text-lg font-bold">{formatPLN(sc.credit_limit_max || 0)}</div>
            <div className="text-xs text-sig-muted">Maksimum</div>
          </div>
          <div className="text-center p-3 bg-sig-surface rounded-xl">
            <div className="text-lg font-bold">{sc.payment_terms_days || 0} dni</div>
            <div className="text-xs text-sig-muted">Termin płatności</div>
          </div>
        </div>
      </div>
    </div>
  );
}

function MaterialsTab({ materials }: { materials: any }) {
  if (!materials?.categories?.length) {
    return <p className="text-sig-muted p-6 text-center">Brak danych do rekomendacji materiałów</p>;
  }
  return (
    <div className="space-y-4">
      <div className="bg-sig-card border border-sig-border rounded-2xl p-5">
        <h3 className="text-sm font-bold text-sig-red mb-2">Rekomendowane kategorie materiałów</h3>
        <p className="text-sm text-sig-muted mb-4">{materials.explanation}</p>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {materials.categories.map((cat: any) => (
            <div key={cat.code} className="bg-sig-surface border border-sig-border rounded-xl p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-bold">{cat.name_pl}</span>
                <span className={`text-xs font-bold px-2 py-0.5 rounded ${
                  cat.confidence >= 0.7 ? "bg-green-500/10 text-green-400" :
                  cat.confidence >= 0.4 ? "bg-yellow-500/10 text-yellow-400" :
                  "bg-sig-border text-sig-muted"
                }`}>{Math.round(cat.confidence * 100)}%</span>
              </div>
              <div className="h-1.5 bg-sig-card rounded-full overflow-hidden mb-2">
                <div className="h-full bg-sig-red rounded-full" style={{ width: `${cat.confidence * 100}%` }} />
              </div>
              <p className="text-xs text-sig-muted">{cat.reason}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function RegistersTab({ snapshot: s, sources, nip }: { snapshot: any; sources: any[]; nip: string }) {
  const links = [
    { label: "Biała Lista VAT", url: `https://wl-api.mf.gov.pl/api/search/nip/${nip}?date=${new Date().toISOString().slice(0,10)}` },
    s.krs && { label: "KRS (eKRS)", url: "https://ekrs.ms.gov.pl/web/wyszukiwarka-krs/strona-glowna/index.html" },
    { label: "CEIDG", url: "https://aplikacja.ceidg.gov.pl/ceidg/ceidg.public.ui/Search.aspx" },
    { label: "GUS REGON", url: "https://wyszukiwarkaregon.stat.gov.pl/" },
    { label: "VIES (EU)", url: `https://ec.europa.eu/taxation_customs/vies/#/vat-validation` },
  ].filter(Boolean);

  return (
    <div className="space-y-4">
      {/* Sources */}
      <div className="bg-sig-card border border-sig-border rounded-2xl p-5">
        <h3 className="text-sm font-bold text-sig-red mb-3">Źródła danych</h3>
        <div className="space-y-2">
          {(sources || []).map((src: any, i: number) => (
            <div key={i} className="flex items-center justify-between p-3 bg-sig-surface rounded-lg border border-sig-border">
              <span className="text-sm font-medium">{src.provider}</span>
              <div className="flex items-center gap-3">
                <span className="text-xs text-sig-muted">{src.fields_count} pól</span>
                <span className={`text-xs font-bold px-2 py-0.5 rounded ${
                  src.status === "ok" ? "bg-green-500/10 text-green-400" : "bg-red-500/10 text-red-400"
                }`}>{src.status}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* PKD Codes */}
      {s.pkd_codes?.length > 0 && (
        <div className="bg-sig-card border border-sig-border rounded-2xl p-5">
          <h3 className="text-sm font-bold text-sig-red mb-3">Kody PKD</h3>
          <div className="space-y-1">
            {s.pkd_codes.map((p: any, i: number) => (
              <div key={i} className="flex gap-3 text-sm py-1">
                <span className={`font-mono ${p.main ? "text-sig-red font-bold" : "text-sig-muted"}`}>{p.code}</span>
                <span>{p.name}</span>
                {p.main && <span className="text-xs bg-sig-red/10 text-sig-red px-2 rounded">główne</span>}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* External links */}
      <div className="bg-sig-card border border-sig-border rounded-2xl p-5">
        <h3 className="text-sm font-bold text-sig-red mb-3">Linki do rejestrów</h3>
        <div className="flex flex-wrap gap-2">
          {links.map((link: any, i: number) => (
            <a key={i} href={link.url} target="_blank" rel="noopener noreferrer"
              className="px-3 py-2 bg-sig-surface border border-sig-border rounded-lg text-sm hover:border-sig-red/30 transition">
              {link.label} ↗
            </a>
          ))}
        </div>
      </div>
    </div>
  );
}

function NotesTab({ nip, token }: { nip: string; token: string }) {
  const [notes, setNotes] = useState<any[]>([]);
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    companiesApi.getNotes(nip, token).then(setNotes).catch(() => {});
  }, [nip, token]);

  const addNote = async () => {
    if (!text.trim()) return;
    setLoading(true);
    try {
      await companiesApi.addNote(nip, text, [], token);
      setText("");
      const updated = await companiesApi.getNotes(nip, token);
      setNotes(updated);
    } catch {}
    setLoading(false);
  };

  return (
    <div className="space-y-4">
      <div className="bg-sig-card border border-sig-border rounded-2xl p-5">
        <h3 className="text-sm font-bold text-sig-red mb-3">Dodaj notatkę</h3>
        <textarea value={text} onChange={e => setText(e.target.value)}
          className="w-full bg-sig-surface border border-sig-border rounded-lg p-3 text-sm h-24 resize-none focus:border-sig-red outline-none"
          placeholder="Wpisz notatkę..." />
        <button onClick={addNote} disabled={loading || !text.trim()}
          className="mt-2 px-4 py-2 bg-sig-red hover:bg-sig-red-dark disabled:opacity-50 rounded-lg text-sm font-bold text-white transition">
          {loading ? "Zapisuję..." : "Zapisz"}
        </button>
      </div>
      {notes.length > 0 && (
        <div className="bg-sig-card border border-sig-border rounded-2xl p-5">
          <h3 className="text-sm font-bold text-sig-red mb-3">Historia notatek</h3>
          {notes.map((note: any) => (
            <div key={note.id} className="border-b border-sig-border/50 last:border-0 py-3">
              <p className="text-sm">{note.text}</p>
              <p className="text-xs text-sig-muted mt-1">{new Date(note.created_at).toLocaleString("pl-PL")}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
