"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { companiesApi } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { formatNIP } from "@/lib/utils";

export default function DashboardPage() {
  const { token } = useAuth();
  const router = useRouter();
  const [nip, setNip] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [recentSearches, setRecent] = useState<any[]>([]);
  const [watchlist, setWatchlist] = useState<any[]>([]);

  useEffect(() => {
    if (!token) return;
    companiesApi.watchlist(token).then(setWatchlist).catch(() => {});
    // Load recent from localStorage
    try {
      const stored = JSON.parse(localStorage.getItem("recent_searches") || "[]");
      setRecent(stored);
    } catch {}
  }, [token]);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    const clean = nip.replace(/[\s-]/g, "");
    if (!/^\d{10}$/.test(clean)) {
      setError("Wpisz prawidłowy 10-cyfrowy NIP");
      return;
    }
    setError("");
    setLoading(true);
    try {
      const result = await companiesApi.lookup(clean, token!);
      // Save to recent
      const recent = [
        { nip: clean, name: result.company?.name, score: result.score?.score_0_100, ts: Date.now() },
        ...recentSearches.filter((r: any) => r.nip !== clean),
      ].slice(0, 20);
      localStorage.setItem("recent_searches", JSON.stringify(recent));
      setRecent(recent);
      router.push(`/company/${clean}`);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Search */}
      <div className="bg-sig-card border border-sig-border rounded-2xl p-6">
        <h2 className="text-lg font-bold mb-4">Sprawdź firmę</h2>
        <form onSubmit={handleSearch} className="flex gap-3">
          <input
            type="text" value={nip} onChange={e => setNip(e.target.value)}
            placeholder="Wpisz NIP (np. 5252344078)"
            className="flex-1 bg-sig-surface border-2 border-sig-border rounded-xl px-4 py-3 text-lg focus:border-sig-red outline-none transition"
          />
          <button type="submit" disabled={loading}
            className="px-8 py-3 bg-sig-red hover:bg-sig-red-dark disabled:opacity-50 rounded-xl font-bold text-white transition whitespace-nowrap">
            {loading ? (
              <span className="flex items-center gap-2">
                <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Szukam...
              </span>
            ) : "Sprawdź"}
          </button>
        </form>
        {error && <div className="mt-3 text-sm text-red-400 bg-red-500/10 border border-red-500/30 rounded-lg p-3">{error}</div>}
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        {/* Recent searches */}
        <div className="bg-sig-card border border-sig-border rounded-2xl p-5">
          <h3 className="text-sm font-bold text-sig-red mb-3">Ostatnie wyszukiwania</h3>
          {recentSearches.length === 0 ? (
            <p className="text-sm text-sig-muted">Brak wyszukiwań</p>
          ) : (
            <div className="space-y-2">
              {recentSearches.slice(0, 8).map((item: any) => (
                <button key={item.nip} onClick={() => router.push(`/company/${item.nip}`)}
                  className="w-full flex items-center justify-between p-3 rounded-lg bg-sig-surface border border-sig-border hover:border-sig-red/30 transition text-left">
                  <div>
                    <div className="text-sm font-semibold">{item.name || item.nip}</div>
                    <div className="text-xs text-sig-muted">{formatNIP(item.nip)}</div>
                  </div>
                  {item.score != null && (
                    <span className={`text-sm font-bold px-2 py-0.5 rounded ${
                      item.score >= 75 ? 'bg-green-500/10 text-green-400' :
                      item.score >= 55 ? 'bg-blue-500/10 text-blue-400' :
                      item.score >= 35 ? 'bg-yellow-500/10 text-yellow-400' :
                      'bg-red-500/10 text-red-400'
                    }`}>{item.score}/100</span>
                  )}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Watchlist */}
        <div className="bg-sig-card border border-sig-border rounded-2xl p-5">
          <h3 className="text-sm font-bold text-sig-red mb-3">Watchlista</h3>
          {watchlist.length === 0 ? (
            <p className="text-sm text-sig-muted">Brak firm na liście obserwacji</p>
          ) : (
            <div className="space-y-2">
              {watchlist.slice(0, 8).map((item: any) => (
                <button key={item.company_nip} onClick={() => router.push(`/company/${item.company_nip}`)}
                  className="w-full flex items-center justify-between p-3 rounded-lg bg-sig-surface border border-sig-border hover:border-sig-red/30 transition text-left">
                  <div>
                    <div className="text-sm font-semibold">{item.company_name || item.company_nip}</div>
                    <div className="text-xs text-sig-muted">{formatNIP(item.company_nip)}</div>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Quick stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: "Sprawdzonych firm", value: recentSearches.length },
          { label: "Na watchliście", value: watchlist.length },
          { label: "Źródła danych", value: "4+" },
          { label: "Komponentów scoringu", value: "11" },
        ].map((stat, i) => (
          <div key={i} className="bg-sig-card border border-sig-border rounded-xl p-4 text-center">
            <div className="text-2xl font-black text-sig-red">{stat.value}</div>
            <div className="text-xs text-sig-muted mt-1">{stat.label}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
