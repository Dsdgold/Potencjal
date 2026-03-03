"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import Link from "next/link";

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

export default function LeadsPage() {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [search, setSearch] = useState("");
  const [tierFilter, setTierFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);

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

  const handleCreate = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    const body = {
      name: fd.get("name"),
      nip: fd.get("nip"),
      city: fd.get("city"),
      employees: fd.get("employees") ? Number(fd.get("employees")) : null,
      revenue_band: fd.get("revenue_band") || null,
    };
    const res = await apiFetch("/api/v1/leads", {
      method: "POST",
      body: JSON.stringify(body),
    });
    if (res.ok) {
      setShowForm(false);
      load();
    }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-white">Leady</h1>
        <button
          onClick={() => setShowForm(!showForm)}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium rounded-lg transition-colors"
        >
          {showForm ? "Anuluj" : "+ Nowy lead"}
        </button>
      </div>

      {/* New Lead Form */}
      {showForm && (
        <form onSubmit={handleCreate} className="bg-slate-800/50 border border-slate-700 rounded-xl p-6 mb-6">
          <h2 className="text-lg font-semibold text-white mb-4">Dodaj leada</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm text-slate-300 mb-1">Nazwa firmy *</label>
              <input name="name" required className="w-full px-3 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-white text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none" />
            </div>
            <div>
              <label className="block text-sm text-slate-300 mb-1">NIP *</label>
              <input name="nip" required pattern="\d{10}" title="10 cyfr" className="w-full px-3 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-white text-sm font-mono focus:ring-2 focus:ring-blue-500 focus:outline-none" />
            </div>
            <div>
              <label className="block text-sm text-slate-300 mb-1">Miasto</label>
              <input name="city" className="w-full px-3 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-white text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none" />
            </div>
            <div>
              <label className="block text-sm text-slate-300 mb-1">Pracownicy</label>
              <input name="employees" type="number" min="0" className="w-full px-3 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-white text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none" />
            </div>
            <div>
              <label className="block text-sm text-slate-300 mb-1">Przychód</label>
              <select name="revenue_band" className="w-full px-3 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-white text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none">
                <option value="">— wybierz —</option>
                <option value="micro">&lt; 2M PLN (mikro)</option>
                <option value="small">2–10M PLN (mała)</option>
                <option value="medium">10–50M PLN (średnia)</option>
                <option value="large">&gt; 50M PLN (duża)</option>
              </select>
            </div>
            <div className="flex items-end">
              <button type="submit" className="w-full py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium rounded-lg transition-colors">
                Zapisz
              </button>
            </div>
          </div>
        </form>
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
          <div className="p-8 text-center text-slate-400">Brak leadów. Kliknij &quot;+ Nowy lead&quot; aby dodać pierwszego.</div>
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
