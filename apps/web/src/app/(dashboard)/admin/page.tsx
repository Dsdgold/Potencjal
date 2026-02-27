"use client";

import { useState, useEffect } from "react";
import { adminApi } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export default function AdminPage() {
  const { token, user } = useAuth();
  const [tab, setTab] = useState("orgs");
  const [orgs, setOrgs] = useState<any[]>([]);
  const [users, setUsers] = useState<any[]>([]);
  const [plans, setPlans] = useState<any[]>([]);
  const [audit, setAudit] = useState<any[]>([]);
  const [health, setHealth] = useState<any>(null);

  useEffect(() => {
    if (!token) return;
    adminApi.orgs(token).then(setOrgs).catch(() => {});
    adminApi.users(token).then(setUsers).catch(() => {});
    adminApi.plans(token).then(setPlans).catch(() => {});
    adminApi.audit(token).then(setAudit).catch(() => {});
    if (user?.role === "superadmin") {
      adminApi.health(token).then(setHealth).catch(() => {});
    }
  }, [token, user]);

  const tabs = [
    { id: "orgs", label: "Organizacje", count: orgs.length },
    { id: "users", label: "Użytkownicy", count: users.length },
    { id: "plans", label: "Plany" },
    { id: "audit", label: "Audit Log", count: audit.length },
    user?.role === "superadmin" && { id: "health", label: "System" },
  ].filter(Boolean);

  return (
    <div className="space-y-4 animate-fade-in">
      <h1 className="text-xl font-bold">Panel administracyjny</h1>

      <div className="flex gap-1 overflow-x-auto">
        {tabs.map((t: any) => (
          <button key={t.id} onClick={() => setTab(t.id)}
            className={`px-4 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition ${
              tab === t.id ? "bg-sig-red/10 text-sig-red" : "text-sig-muted hover:text-white"
            }`}>
            {t.label} {t.count != null && <span className="ml-1 opacity-60">({t.count})</span>}
          </button>
        ))}
      </div>

      {tab === "orgs" && (
        <div className="bg-sig-card border border-sig-border rounded-2xl overflow-hidden">
          <table className="w-full text-sm">
            <thead><tr className="bg-sig-surface text-sig-muted text-left">
              <th className="px-4 py-3">Nazwa</th><th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Plan</th><th className="px-4 py-3">Utworzona</th>
            </tr></thead>
            <tbody>
              {orgs.map(o => (
                <tr key={o.id} className="border-t border-sig-border/50 hover:bg-sig-surface/50">
                  <td className="px-4 py-3 font-medium">{o.name}</td>
                  <td className="px-4 py-3">
                    <span className={`text-xs px-2 py-0.5 rounded ${o.status === 'active' ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'}`}>
                      {o.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sig-muted">{o.plan_name || "—"}</td>
                  <td className="px-4 py-3 text-sig-muted">{new Date(o.created_at).toLocaleDateString("pl-PL")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === "users" && (
        <div className="bg-sig-card border border-sig-border rounded-2xl overflow-hidden">
          <table className="w-full text-sm">
            <thead><tr className="bg-sig-surface text-sig-muted text-left">
              <th className="px-4 py-3">Email</th><th className="px-4 py-3">Imię</th>
              <th className="px-4 py-3">Rola</th><th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Ostatnie logowanie</th>
            </tr></thead>
            <tbody>
              {users.map((u: any) => (
                <tr key={u.id} className="border-t border-sig-border/50 hover:bg-sig-surface/50">
                  <td className="px-4 py-3 font-medium">{u.email}</td>
                  <td className="px-4 py-3">{u.full_name}</td>
                  <td className="px-4 py-3">
                    <span className="text-xs px-2 py-0.5 rounded bg-sig-red/10 text-sig-red">{u.role}</span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`text-xs ${u.is_active ? 'text-green-400' : 'text-red-400'}`}>
                      {u.is_active ? "Aktywny" : "Nieaktywny"}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sig-muted">
                    {u.last_login ? new Date(u.last_login).toLocaleString("pl-PL") : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === "plans" && (
        <div className="grid md:grid-cols-3 gap-4">
          {plans.map((p: any) => (
            <div key={p.id} className="bg-sig-card border border-sig-border rounded-2xl p-5">
              <h3 className="text-lg font-bold">{p.name}</h3>
              <p className="text-sig-muted text-sm">Kod: {p.code}</p>
              <p className="text-xl font-black mt-2">{(p.price_monthly / 100).toFixed(0)} PLN/mies.</p>
              <div className="mt-3 text-xs text-sig-muted space-y-1">
                <p>Limity: {JSON.stringify(p.limits_json)}</p>
                <p>Funkcje: {Object.entries(p.features_json).filter(([,v]) => v).map(([k]) => k).join(", ")}</p>
              </div>
            </div>
          ))}
        </div>
      )}

      {tab === "audit" && (
        <div className="bg-sig-card border border-sig-border rounded-2xl overflow-hidden">
          <table className="w-full text-sm">
            <thead><tr className="bg-sig-surface text-sig-muted text-left">
              <th className="px-4 py-3">Czas</th><th className="px-4 py-3">Akcja</th>
              <th className="px-4 py-3">Cel</th><th className="px-4 py-3">Cel</th>
            </tr></thead>
            <tbody>
              {audit.slice(0, 50).map((log: any) => (
                <tr key={log.id} className="border-t border-sig-border/50">
                  <td className="px-4 py-2 text-sig-muted">{new Date(log.created_at).toLocaleString("pl-PL")}</td>
                  <td className="px-4 py-2 font-medium">{log.action}</td>
                  <td className="px-4 py-2 text-sig-muted">{log.target_type}</td>
                  <td className="px-4 py-2 text-sig-muted font-mono text-xs">{log.target_id?.slice(0, 12)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === "health" && health && (
        <div className="grid md:grid-cols-3 gap-4">
          {[
            { label: "Baza danych", value: health.db_status },
            { label: "Redis", value: health.redis_status },
            { label: "Qdrant", value: health.qdrant_status },
            { label: "Kolejka", value: health.queue_depth },
            { label: "Aktywne org.", value: health.active_orgs },
            { label: "Zapytania dziś", value: health.lookups_today },
          ].map((item, i) => (
            <div key={i} className="bg-sig-card border border-sig-border rounded-xl p-4">
              <div className="text-xs text-sig-muted">{item.label}</div>
              <div className={`text-xl font-bold mt-1 ${
                item.value === "ok" ? "text-green-400" : item.value === "error" ? "text-red-400" : "text-sig-text"
              }`}>{item.value}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
