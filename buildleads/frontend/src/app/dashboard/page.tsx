"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import Link from "next/link";

interface Lead {
  id: string;
  name: string;
  nip: string;
  city: string;
  score: number | null;
  tier: string | null;
  annual_potential: number | null;
  created_at: string;
}

interface Stats {
  total: number;
  byTier: Record<string, number>;
  avgScore: number;
  totalPotential: number;
}

const tierConfig: Record<string, { bg: string; text: string; border: string; glow: string }> = {
  S: { bg: "bg-[#22c55e]/8", text: "text-[#4ade80]", border: "border-[#22c55e]/15", glow: "shadow-[#22c55e]/10" },
  A: { bg: "bg-[#0ea5e9]/8", text: "text-[#7dd3fc]", border: "border-[#0ea5e9]/15", glow: "shadow-[#0ea5e9]/10" },
  B: { bg: "bg-[#f59e0b]/8", text: "text-[#fbbf24]", border: "border-[#f59e0b]/15", glow: "shadow-[#f59e0b]/10" },
  C: { bg: "bg-[#455566]/8", text: "text-[#7b8fa0]", border: "border-[#455566]/15", glow: "shadow-[#455566]/10" },
};

export default function DashboardPage() {
  const { user } = useAuth();
  const [leads, setLeads] = useState<Lead[]>([]);
  const [stats, setStats] = useState<Stats>({ total: 0, byTier: {}, avgScore: 0, totalPotential: 0 });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      const res = await apiFetch("/api/v1/leads?limit=100");
      if (res.ok) {
        const data = await res.json();
        const items: Lead[] = data.items || data;
        setLeads(items);

        const byTier: Record<string, number> = { S: 0, A: 0, B: 0, C: 0 };
        let scoreSum = 0, scoreCount = 0, potentialSum = 0;
        items.forEach((l) => {
          if (l.tier && byTier[l.tier] !== undefined) byTier[l.tier]++;
          if (l.score != null) { scoreSum += l.score; scoreCount++; }
          if (l.annual_potential) potentialSum += l.annual_potential;
        });
        setStats({ total: items.length, byTier, avgScore: scoreCount ? Math.round(scoreSum / scoreCount) : 0, totalPotential: potentialSum });
      }
      setLoading(false);
    }
    load();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-2 border-[#0ea5e9] border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="grid-bg min-h-full">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-[#e8edf2]">Dashboard</h1>
          <p className="text-[#455566] text-sm mt-1">Witaj, {user?.first_name || "uzytkowniku"}. Oto przeglad Twoich leadow.</p>
        </div>
        <Link
          href="/leads"
          className="px-5 py-2.5 bg-gradient-to-r from-[#0ea5e9] to-[#38bdf8] hover:from-[#38bdf8] hover:to-[#7dd3fc] text-white text-sm font-semibold rounded-xl transition-all shadow-lg shadow-[#0ea5e9]/25 hover:shadow-[#0ea5e9]/35 hover:-translate-y-0.5 active:translate-y-0"
        >
          + Sprawdz firme
        </Link>
      </div>

      {/* Quick NIP check */}
      <div className="bg-[#0f171e] border border-[rgba(14,165,233,0.08)] rounded-2xl p-7 mb-7 relative overflow-hidden">
        <div className="absolute top-0 right-0 w-80 h-80 bg-[#0ea5e9]/4 rounded-full blur-[120px] -translate-y-1/2 translate-x-1/3" />
        <div className="absolute bottom-0 left-0 w-56 h-56 bg-[#a855f7]/3 rounded-full blur-[100px] translate-y-1/2 -translate-x-1/4" />
        <div className="relative">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[#0ea5e9] to-[#38bdf8] flex items-center justify-center">
              <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
              </svg>
            </div>
            <h2 className="text-lg font-bold text-[#e8edf2]">Szybkie sprawdzenie</h2>
          </div>
          <p className="text-[#7b8fa0] text-sm mb-5 ml-11">Wpisz NIP — automatycznie pobierzemy dane i policzymy potencjal</p>
          <form onSubmit={(e) => { e.preventDefault(); const v = (e.currentTarget.elements.namedItem("qnip") as HTMLInputElement).value.replace(/[\s-]/g, ""); if (/^\d{10}$/.test(v)) { window.location.href = `/leads?nip=${v}`; } }} className="flex gap-3 ml-11">
            <input
              name="qnip"
              placeholder="Wpisz NIP, np. 5272700021"
              className="flex-1 max-w-xs px-4 py-3 bg-[#020709] border border-[rgba(14,165,233,0.1)] rounded-xl text-[#e8edf2] font-mono text-lg tracking-wider placeholder-[#455566] focus:ring-2 focus:ring-[#0ea5e9]/40 focus:border-[#0ea5e9]/30 focus:outline-none transition-all"
              maxLength={13}
            />
            <button type="submit" className="px-7 py-3 bg-gradient-to-r from-[#22c55e] to-[#4ade80] hover:from-[#4ade80] hover:to-[#86efac] text-white font-semibold rounded-xl transition-all shadow-lg shadow-[#22c55e]/20 hover:shadow-[#22c55e]/30">
              Sprawdz
            </button>
          </form>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-7">
        <KpiCard label="Wszystkie leady" value={stats.total.toString()} icon="chart" />
        <KpiCard label="Sredni score" value={stats.avgScore.toString()} suffix="/100" icon="score" />
        <KpiCard label="Potencjal roczny" value={stats.totalPotential > 0 ? `${(stats.totalPotential / 1000).toFixed(0)}k` : "—"} suffix=" PLN" icon="money" />
        <KpiCard label="Tier S (priorytet)" value={stats.byTier.S?.toString() || "0"} accent icon="star" />
      </div>

      {/* Tier Distribution */}
      <div className="bg-[#0f171e] border border-[rgba(14,165,233,0.08)] rounded-2xl p-6 mb-7">
        <h2 className="text-xs font-semibold text-[#7b8fa0] mb-5 uppercase tracking-[0.15em]">Rozklad tierow</h2>
        <div className="grid grid-cols-4 gap-4">
          {(["S", "A", "B", "C"] as const).map((tier) => {
            const tc = tierConfig[tier];
            return (
              <div key={tier} className={`text-center p-5 rounded-2xl border transition-all hover:scale-[1.03] hover-lift ${tc.bg} ${tc.border} shadow-sm ${tc.glow}`}>
                <div className={`text-3xl font-black ${tc.text}`}>{stats.byTier[tier] || 0}</div>
                <div className={`text-xs mt-2 font-semibold ${tc.text} opacity-60`}>Tier {tier}</div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Recent Leads */}
      <div className="bg-[#0f171e] border border-[rgba(14,165,233,0.08)] rounded-2xl overflow-hidden">
        <div className="px-6 py-4 flex items-center justify-between">
          <h2 className="text-xs font-semibold text-[#7b8fa0] uppercase tracking-[0.15em]">Ostatnie leady</h2>
          <Link href="/leads" className="text-xs text-[#0ea5e9] hover:text-[#38bdf8] font-medium transition-colors">
            Zobacz wszystkie →
          </Link>
        </div>
        {leads.length === 0 ? (
          <p className="text-[#455566] text-sm px-6 pb-6">Brak leadow. Kliknij &quot;+ Sprawdz firme&quot; aby dodac pierwszego leada.</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-[#455566] border-t border-[rgba(14,165,233,0.06)] bg-[#0a1014]/60">
                <th className="text-left py-3 px-5 font-medium text-[10px] uppercase tracking-[0.15em]">Nazwa</th>
                <th className="text-left py-3 px-5 font-medium text-[10px] uppercase tracking-[0.15em]">NIP</th>
                <th className="text-left py-3 px-5 font-medium text-[10px] uppercase tracking-[0.15em]">Miasto</th>
                <th className="text-center py-3 px-5 font-medium text-[10px] uppercase tracking-[0.15em]">Score</th>
                <th className="text-center py-3 px-5 font-medium text-[10px] uppercase tracking-[0.15em]">Tier</th>
                <th className="text-right py-3 px-5 font-medium text-[10px] uppercase tracking-[0.15em]">Potencjal</th>
              </tr>
            </thead>
            <tbody>
              {leads.slice(0, 10).map((lead) => {
                const tc = lead.tier ? tierConfig[lead.tier] : null;
                return (
                  <tr key={lead.id} className="border-t border-[rgba(14,165,233,0.04)] hover:bg-[#162028] transition-colors">
                    <td className="py-3.5 px-5">
                      <Link href={`/leads/${lead.id}`} className="text-[#7dd3fc] hover:text-[#bae6fd] font-medium transition-colors">
                        {lead.name}
                      </Link>
                    </td>
                    <td className="py-3.5 px-5 text-[#455566] font-mono text-xs">{lead.nip}</td>
                    <td className="py-3.5 px-5 text-[#7b8fa0]">{lead.city || "—"}</td>
                    <td className="py-3.5 px-5 text-center">
                      <span className="text-[#e8edf2] font-bold">{lead.score ?? "—"}</span>
                    </td>
                    <td className="py-3.5 px-5 text-center">
                      {lead.tier && tc ? (
                        <span className={`inline-block px-2.5 py-1 rounded-lg text-[11px] font-bold border ${tc.bg} ${tc.text} ${tc.border}`}>
                          {lead.tier}
                        </span>
                      ) : "—"}
                    </td>
                    <td className="py-3.5 px-5 text-right text-[#7b8fa0]">
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

function KpiCard({ label, value, suffix, accent, icon }: { label: string; value: string; suffix?: string; accent?: boolean; icon?: string }) {
  const icons: Record<string, React.ReactNode> = {
    chart: <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z" /></svg>,
    score: <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M3.75 3v11.25A2.25 2.25 0 006 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0118 16.5h-2.25m-7.5 0h7.5m-7.5 0l-1 3m8.5-3l1 3m0 0l.5 1.5m-.5-1.5h-9.5m0 0l-.5 1.5" /></svg>,
    money: <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M12 6v12m-3-2.818l.879.659c1.171.879 3.07.879 4.242 0 1.172-.879 1.172-2.303 0-3.182C13.536 12.219 12.768 12 12 12c-.725 0-1.45-.22-2.003-.659-1.106-.879-1.106-2.303 0-3.182s2.9-.879 4.006 0l.415.33M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>,
    star: <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M15.59 14.37a6 6 0 01-5.84 7.38v-4.8m5.84-2.58a14.98 14.98 0 006.16-12.12A14.98 14.98 0 009.631 8.41m5.96 5.96a14.926 14.926 0 01-5.841 2.58m-.119-8.54a6 6 0 00-7.381 5.84h4.8m2.581-5.84a14.927 14.927 0 00-2.58 5.84m2.699 2.7c-.103.021-.207.041-.311.06a15.09 15.09 0 01-2.448-2.448 14.9 14.9 0 01.06-.312m-2.24 2.39a4.493 4.493 0 00-1.757 4.306 4.493 4.493 0 004.306-1.758M16.5 9a1.5 1.5 0 11-3 0 1.5 1.5 0 013 0z" /></svg>,
  };

  return (
    <div className={`p-5 rounded-2xl border transition-all hover-lift ${accent ? "bg-[#22c55e]/5 border-[#22c55e]/15" : "bg-[#0f171e] border-[rgba(14,165,233,0.08)]"}`}>
      <div className="flex items-center gap-2 mb-3">
        <div className={`w-7 h-7 rounded-lg flex items-center justify-center ${accent ? "bg-[#22c55e]/10 text-[#4ade80]" : "bg-[#0ea5e9]/10 text-[#0ea5e9]"}`}>
          {icon && icons[icon]}
        </div>
        <p className="text-[10px] text-[#455566] uppercase tracking-[0.15em] font-semibold">{label}</p>
      </div>
      <p className={`text-2xl font-black ${accent ? "text-[#4ade80]" : "text-[#e8edf2]"}`}>
        {value}<span className="text-sm font-normal text-[#455566] ml-1">{suffix}</span>
      </p>
    </div>
  );
}
