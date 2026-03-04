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
  S: "bg-[#10b981]/10 text-[#10b981] border-[#10b981]/20",
  A: "bg-[#6366f1]/10 text-[#a5b4fc] border-[#6366f1]/20",
  B: "bg-[#f59e0b]/10 text-[#f59e0b] border-[#f59e0b]/20",
  C: "bg-[#5e5e73]/10 text-[#9494a8] border-[#5e5e73]/20",
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
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-[#5e5e73] text-sm">Ładowanie dashboardu...</div>
      </div>
    );
  }

  return (
    <div className="grid-bg min-h-full">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-xl font-bold text-[#ededf0]">Dashboard</h1>
          <p className="text-[#5e5e73] text-sm mt-0.5">Witaj, {user?.first_name || "użytkowniku"}</p>
        </div>
        <Link
          href="/leads"
          className="px-5 py-2.5 bg-gradient-to-r from-[#6366f1] to-[#818cf8] hover:from-[#818cf8] hover:to-[#a78bfa] text-white text-sm font-semibold rounded-xl transition-all shadow-lg shadow-[#6366f1]/20 hover:shadow-[#6366f1]/30 hover:-translate-y-0.5 active:translate-y-0"
        >
          + Sprawdź firmę
        </Link>
      </div>

      {/* Quick NIP check */}
      <div className="bg-[#16161f] border border-[#26263a] rounded-2xl p-6 mb-6 relative overflow-hidden">
        <div className="absolute top-0 right-0 w-72 h-72 bg-[#6366f1]/5 rounded-full blur-[100px] -translate-y-1/2 translate-x-1/3" />
        <div className="absolute bottom-0 left-0 w-48 h-48 bg-[#8b5cf6]/3 rounded-full blur-[80px] translate-y-1/2 -translate-x-1/4" />
        <div className="relative">
          <h2 className="text-base font-semibold text-[#ededf0] mb-1">Szybkie sprawdzenie</h2>
          <p className="text-[#5e5e73] text-sm mb-4">Wpisz NIP — automatycznie pobierzemy dane i policzymy potencjał</p>
          <form onSubmit={(e) => { e.preventDefault(); const v = (e.currentTarget.elements.namedItem("qnip") as HTMLInputElement).value.replace(/[\s-]/g, ""); if (/^\d{10}$/.test(v)) { window.location.href = `/leads?nip=${v}`; } }} className="flex gap-3">
            <input
              name="qnip"
              placeholder="Wpisz NIP, np. 5272700021"
              className="flex-1 max-w-xs px-4 py-2.5 bg-[#0a0a0f] border border-[#26263a] rounded-lg text-[#ededf0] font-mono text-lg tracking-wider placeholder-[#5e5e73] focus:ring-2 focus:ring-[#6366f1]/50 focus:outline-none"
              maxLength={13}
            />
            <button type="submit" className="px-6 py-2.5 bg-[#10b981] hover:bg-[#34d399] text-white font-medium rounded-lg transition-all glow-success">
              Sprawdź
            </button>
          </form>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
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
      <div className="bg-[#16161f] border border-[#26263a] rounded-2xl p-5 mb-6">
        <h2 className="text-sm font-semibold text-[#ededf0] mb-4 uppercase tracking-wider">Rozklad tierow</h2>
        <div className="grid grid-cols-4 gap-3">
          {(["S", "A", "B", "C"] as const).map((tier) => (
            <div key={tier} className={`text-center p-5 rounded-xl border transition-all hover:scale-105 ${tierColors[tier]}`}>
              <div className="text-3xl font-bold">{stats.byTier[tier] || 0}</div>
              <div className="text-xs mt-1.5 opacity-70 font-medium">Tier {tier}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Recent Leads */}
      <div className="bg-[#16161f] border border-[#26263a] rounded-2xl overflow-hidden">
        <div className="px-5 py-4">
          <h2 className="text-sm font-semibold text-[#ededf0] uppercase tracking-wider">Ostatnie leady</h2>
        </div>
        {leads.length === 0 ? (
          <p className="text-[#5e5e73] text-sm px-5 pb-5">Brak leadów. Dodaj pierwszego leada.</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-[#5e5e73] border-t border-[#26263a] bg-[#111118]/50">
                <th className="text-left py-3 px-4 font-medium text-xs uppercase tracking-wider">Nazwa</th>
                <th className="text-left py-3 px-4 font-medium text-xs uppercase tracking-wider">NIP</th>
                <th className="text-left py-3 px-4 font-medium text-xs uppercase tracking-wider">Miasto</th>
                <th className="text-center py-3 px-4 font-medium text-xs uppercase tracking-wider">Score</th>
                <th className="text-center py-3 px-4 font-medium text-xs uppercase tracking-wider">Tier</th>
                <th className="text-right py-3 px-4 font-medium text-xs uppercase tracking-wider">Potencjał</th>
              </tr>
            </thead>
            <tbody>
              {leads.slice(0, 10).map((lead) => (
                <tr key={lead.id} className="border-t border-[#26263a]/50 hover:bg-[#1c1c28] transition-colors">
                  <td className="py-3 px-4">
                    <Link href={`/leads/${lead.id}`} className="text-[#a5b4fc] hover:text-[#c7d2fe] font-medium">
                      {lead.name}
                    </Link>
                  </td>
                  <td className="py-3 px-4 text-[#5e5e73] font-mono text-xs">{lead.nip}</td>
                  <td className="py-3 px-4 text-[#9494a8]">{lead.city || "—"}</td>
                  <td className="py-3 px-4 text-center">
                    <span className="text-[#ededf0] font-semibold">{lead.score ?? "—"}</span>
                  </td>
                  <td className="py-3 px-4 text-center">
                    {lead.tier ? (
                      <span className={`inline-block px-2 py-0.5 rounded text-xs font-bold border ${tierColors[lead.tier] || ""}`}>
                        {lead.tier}
                      </span>
                    ) : "—"}
                  </td>
                  <td className="py-3 px-4 text-right text-[#9494a8]">
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
    <div className={`p-5 rounded-xl border transition-all hover:translate-y-[-2px] hover:shadow-lg ${accent ? "bg-[#10b981]/5 border-[#10b981]/20 hover:shadow-[#10b981]/5" : "bg-[#16161f] border-[#26263a] hover:border-[#33334d] hover:shadow-[#6366f1]/5"}`}>
      <p className="text-xs text-[#5e5e73] mb-2 uppercase tracking-wider font-medium">{label}</p>
      <p className={`text-2xl font-bold ${accent ? "text-[#10b981]" : "text-[#ededf0]"}`}>
        {value}<span className="text-sm font-normal text-[#5e5e73] ml-0.5">{suffix}</span>
      </p>
    </div>
  );
}
