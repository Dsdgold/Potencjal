"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { login } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  const { reload } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email, password);
      await reload();
      router.push("/dashboard");
    } catch {
      setError("Nieprawidlowy email lub haslo");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#020709] relative overflow-hidden">
      {/* Background grid */}
      <div className="grid-bg absolute inset-0" />

      {/* Ambient glow */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[600px] h-[400px] bg-[#0ea5e9]/5 rounded-full blur-[120px]" />
      <div className="absolute bottom-1/4 right-1/4 w-[300px] h-[300px] bg-[#a855f7]/4 rounded-full blur-[100px]" />

      <div className="w-full max-w-sm relative z-10 animate-slide-up">
        <div className="text-center mb-10">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-[#0ea5e9] to-[#38bdf8] flex items-center justify-center mx-auto mb-4 shadow-lg shadow-[#0ea5e9]/20">
            <span className="text-white font-black text-lg">BL</span>
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-[#e8edf2]">
            Build<span className="gradient-text">Leads</span>
          </h1>
          <p className="text-[#455566] mt-2 text-sm">Platforma oceny potencjalu klientow B2B</p>
        </div>

        <form onSubmit={handleSubmit} className="bg-[#0f171e] border border-[rgba(14,165,233,0.08)] rounded-2xl p-8">
          <h2 className="text-lg font-semibold text-[#e8edf2] mb-6">Zaloguj sie</h2>

          {error && (
            <div className="bg-[#ef4444]/8 border border-[#ef4444]/20 text-[#ef4444] px-4 py-3 rounded-xl mb-4 text-sm">
              {error}
            </div>
          )}

          <div className="space-y-4">
            <div>
              <label className="block text-[10px] font-semibold text-[#455566] mb-1.5 uppercase tracking-[0.15em]">Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-4 py-2.5 bg-[#020709] border border-[rgba(14,165,233,0.08)] rounded-xl text-[#e8edf2] placeholder-[#455566] focus:outline-none focus:ring-2 focus:ring-[#0ea5e9]/30 focus:border-[#0ea5e9]/30 transition-all"
                placeholder="admin@buildleads.pl"
                required
              />
            </div>
            <div>
              <label className="block text-[10px] font-semibold text-[#455566] mb-1.5 uppercase tracking-[0.15em]">Haslo</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-4 py-2.5 bg-[#020709] border border-[rgba(14,165,233,0.08)] rounded-xl text-[#e8edf2] placeholder-[#455566] focus:outline-none focus:ring-2 focus:ring-[#0ea5e9]/30 focus:border-[#0ea5e9]/30 transition-all"
                placeholder="••••••••"
                required
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full mt-6 py-3 px-4 bg-gradient-to-r from-[#0ea5e9] to-[#38bdf8] hover:from-[#38bdf8] hover:to-[#7dd3fc] disabled:opacity-40 text-white font-semibold rounded-xl transition-all shadow-lg shadow-[#0ea5e9]/25 hover:shadow-[#0ea5e9]/40"
          >
            {loading ? (
              <div className="flex items-center justify-center gap-2">
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Logowanie...
              </div>
            ) : "Zaloguj sie"}
          </button>

          <p className="mt-4 text-center text-xs text-[#455566]">
            Demo: admin@buildleads.pl / admin123
          </p>
        </form>
      </div>
    </div>
  );
}
