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

const tierColors: Record<string, string> = {
  S: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
  A: "bg-blue-500/20 text-blue-400 border-blue-500/30",
  B: "bg-amber-500/20 text-amber-400 border-amber-500/30",
  C: "bg-slate-500/20 text-slate-400 border-slate-500/30",
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
        let scoreSum = 0;
        let scoreCount = 0;
        let potentialSum = 0;

        items.forEach((l) => {
          if (l.tier && byTier[l.tier] !== undefined) byTier[l.tier]++;
          if (l.score != null) { scoreSum += l.score; scoreCount++; }
          if (l.annual_potential) potentialSum += l.annual_potential;
        });

        setStats({
          total: items.length,
          byTier,
          avgScore: scoreCount ? Math.round(scoreSum / scoreCount) : 0,
          totalPotential: potentialSum,
        });
      }
      setLoading(false);
    }
    load();
  }, []);

  if (loading) {
    return <div className="text-slate-400">Ładowanie dashboardu...</div>;
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white">Dashboard</h1>
          <p className="text-slate-400 mt-1">Witaj, {user?.first_name || "użytkowniku"}</p>
        </div>
        <Link
          href="/leads"
          className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium rounded-lg transition-colors"
        >
          + Sprawdź firmę
        </Link>
      </div>

      {/* Quick NIP check */}
      <div className="bg-gradient-to-r from-blue-600/20 to-emerald-600/20 border border-blue-500/30 rounded-xl p-6 mb-8">
        <h2 className="text-lg font-semibold text-white mb-1">Szybkie sprawdzenie</h2>
        <p className="text-slate-400 text-sm mb-3">Wpisz NIP firmy — automatycznie pobierzemy dane i policzymy potencjał</p>
        <form onSubmit={(e) => { e.preventDefault(); const v = (e.currentTarget.elements.namedItem("qnip") as HTMLInputElement).value.replace(/[\s-]/g, ""); if (/^\d{10}$/.test(v)) { window.location.href = `/leads?nip=${v}`; } }} className="flex gap-3">
          <input
            name="qnip"
            placeholder="Wpisz NIP, np. 5272700021"
            className="flex-1 max-w-xs px-4 py-2.5 bg-slate-700/50 border border-slate-600 rounded-lg text-white font-mono text-lg tracking-wider focus:ring-2 focus:ring-blue-500 focus:outline-none"
            maxLength={13}
          />
          <button type="submit" className="px-6 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white font-medium rounded-lg transition-colors">
            Sprawdź
          </button>
        </form>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <KpiCard label="Wszystkie leady" value={stats.total.toString()} />
        <KpiCard label="Średni score" value={stats.avgScore.toString()} suffix="/100" />
        <KpiCard
          label="Potencjał roczny"
          value={stats.totalPotential > 0 ? `${(stats.totalPotential / 1000).toFixed(0)}k` : "—"}
          suffix=" PLN"
        />
        <KpiCard label="Tier S (priorytet)" value={stats.byTier.S?.toString() || "0"} accent />
      </div>

      {/* Tier Distribution */}
      <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6 mb-8">
        <h2 className="text-lg font-semibold text-white mb-4">Rozkład tierów</h2>
        <div className="grid grid-cols-4 gap-4">
          {(["S", "A", "B", "C"] as const).map((tier) => (
            <div key={tier} className={`text-center p-4 rounded-lg border ${tierColors[tier]}`}>
              <div className="text-3xl font-bold">{stats.byTier[tier] || 0}</div>
              <div className="text-sm mt-1">Tier {tier}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Recent Leads */}
      <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
        <h2 className="text-lg font-semibold text-white mb-4">Ostatnie leady</h2>
        {leads.length === 0 ? (
          <p className="text-slate-400 text-sm">Brak leadów. Dodaj pierwszego leada.</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-slate-400 border-b border-slate-700">
                <th className="text-left py-3 px-2 font-medium">Nazwa</th>
                <th className="text-left py-3 px-2 font-medium">NIP</th>
                <th className="text-left py-3 px-2 font-medium">Miasto</th>
                <th className="text-center py-3 px-2 font-medium">Score</th>
                <th className="text-center py-3 px-2 font-medium">Tier</th>
                <th className="text-right py-3 px-2 font-medium">Potencjał</th>
              </tr>
            </thead>
            <tbody>
              {leads.slice(0, 10).map((lead) => (
                <tr key={lead.id} className="border-b border-slate-700/50 hover:bg-slate-700/20 transition-colors">
                  <td className="py-3 px-2">
                    <Link href={`/leads/${lead.id}`} className="text-blue-400 hover:text-blue-300">
                      {lead.name}
                    </Link>
                  </td>
                  <td className="py-3 px-2 text-slate-300 font-mono text-xs">{lead.nip}</td>
                  <td className="py-3 px-2 text-slate-300">{lead.city || "—"}</td>
                  <td className="py-3 px-2 text-center">
                    <span className="text-white font-medium">{lead.score ?? "—"}</span>
                  </td>
                  <td className="py-3 px-2 text-center">
                    {lead.tier ? (
                      <span className={`inline-block px-2 py-0.5 rounded text-xs font-bold border ${tierColors[lead.tier] || ""}`}>
                        {lead.tier}
                      </span>
                    ) : "—"}
                  </td>
                  <td className="py-3 px-2 text-right text-slate-300">
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

function KpiCard({ label, value, suffix, accent }: { label: string; value: string; suffix?: string; accent?: boolean }) {
  return (
    <div className={`p-5 rounded-xl border ${accent ? "bg-emerald-500/10 border-emerald-500/30" : "bg-slate-800/50 border-slate-700"}`}>
      <p className="text-sm text-slate-400 mb-1">{label}</p>
      <p className={`text-2xl font-bold ${accent ? "text-emerald-400" : "text-white"}`}>
        {value}<span className="text-sm font-normal text-slate-400">{suffix}</span>
      </p>
    </div>
  );
}
