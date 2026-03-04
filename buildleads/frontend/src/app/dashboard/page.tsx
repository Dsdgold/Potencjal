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
  S: "bg-emerald-50 text-emerald-700 border-emerald-200",
  A: "bg-blue-50 text-blue-700 border-blue-200",
  B: "bg-amber-50 text-amber-700 border-amber-200",
  C: "bg-gray-100 text-gray-600 border-gray-200",
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
    return <div className="text-gray-400">Ładowanie dashboardu...</div>;
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-500 mt-1">Witaj, {user?.first_name || "użytkowniku"}</p>
        </div>
        <Link
          href="/leads"
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg transition-colors"
        >
          + Sprawdź firmę
        </Link>
      </div>

      {/* Quick NIP check */}
      <div className="bg-gradient-to-r from-blue-50 to-emerald-50 border border-blue-200 rounded-xl p-6 mb-8">
        <h2 className="text-lg font-semibold text-gray-900 mb-1">Szybkie sprawdzenie</h2>
        <p className="text-gray-500 text-sm mb-3">Wpisz NIP firmy — automatycznie pobierzemy dane i policzymy potencjał</p>
        <form onSubmit={(e) => { e.preventDefault(); const v = (e.currentTarget.elements.namedItem("qnip") as HTMLInputElement).value.replace(/[\s-]/g, ""); if (/^\d{10}$/.test(v)) { window.location.href = `/leads?nip=${v}`; } }} className="flex gap-3">
          <input
            name="qnip"
            placeholder="Wpisz NIP, np. 5272700021"
            className="flex-1 max-w-xs px-4 py-2.5 bg-white border border-gray-300 rounded-lg text-gray-900 font-mono text-lg tracking-wider focus:ring-2 focus:ring-blue-500 focus:outline-none"
            maxLength={13}
          />
          <button type="submit" className="px-6 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white font-medium rounded-lg transition-colors">
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
      <div className="bg-white border border-gray-200 rounded-xl p-6 mb-8 shadow-sm">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Rozkład tierów</h2>
        <div className="grid grid-cols-4 gap-4">
          {(["S", "A", "B", "C"] as const).map((tier) => (
            <div key={tier} className={`text-center p-4 rounded-lg border ${tierColors[tier]}`}>
              <div className="text-3xl font-bold">{stats.byTier[tier] || 0}</div>
              <div className="text-sm mt-1 opacity-80">Tier {tier}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Recent Leads */}
      <div className="bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden">
        <div className="p-6 pb-0">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Ostatnie leady</h2>
        </div>
        {leads.length === 0 ? (
          <p className="text-gray-400 text-sm p-6 pt-0">Brak leadów. Dodaj pierwszego leada.</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-gray-500 border-b border-gray-100 bg-gray-50/50">
                <th className="text-left py-3 px-4 font-medium">Nazwa</th>
                <th className="text-left py-3 px-4 font-medium">NIP</th>
                <th className="text-left py-3 px-4 font-medium">Miasto</th>
                <th className="text-center py-3 px-4 font-medium">Score</th>
                <th className="text-center py-3 px-4 font-medium">Tier</th>
                <th className="text-right py-3 px-4 font-medium">Potencjał</th>
              </tr>
            </thead>
            <tbody>
              {leads.slice(0, 10).map((lead) => (
                <tr key={lead.id} className="border-b border-gray-50 hover:bg-gray-50 transition-colors">
                  <td className="py-3 px-4">
                    <Link href={`/leads/${lead.id}`} className="text-blue-600 hover:text-blue-800 font-medium">
                      {lead.name}
                    </Link>
                  </td>
                  <td className="py-3 px-4 text-gray-500 font-mono text-xs">{lead.nip}</td>
                  <td className="py-3 px-4 text-gray-600">{lead.city || "—"}</td>
                  <td className="py-3 px-4 text-center">
                    <span className="text-gray-900 font-semibold">{lead.score ?? "—"}</span>
                  </td>
                  <td className="py-3 px-4 text-center">
                    {lead.tier ? (
                      <span className={`inline-block px-2 py-0.5 rounded text-xs font-bold border ${tierColors[lead.tier] || ""}`}>
                        {lead.tier}
                      </span>
                    ) : "—"}
                  </td>
                  <td className="py-3 px-4 text-right text-gray-600">
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
    <div className={`p-5 rounded-xl border shadow-sm ${accent ? "bg-emerald-50 border-emerald-200" : "bg-white border-gray-200"}`}>
      <p className="text-sm text-gray-500 mb-1">{label}</p>
      <p className={`text-2xl font-bold ${accent ? "text-emerald-700" : "text-gray-900"}`}>
        {value}<span className="text-sm font-normal text-gray-400">{suffix}</span>
      </p>
    </div>
  );
}
