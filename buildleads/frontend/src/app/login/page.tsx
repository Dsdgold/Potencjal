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
      setError("Nieprawidłowy email lub hasło");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#0a0a0f] relative overflow-hidden">
      {/* Background grid effect */}
      <div className="absolute inset-0 opacity-[0.02]" style={{ backgroundImage: "radial-gradient(circle at 1px 1px, white 1px, transparent 0)", backgroundSize: "40px 40px" }} />

      {/* Ambient glow */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[600px] h-[400px] bg-[#6366f1]/5 rounded-full blur-[120px]" />

      <div className="w-full max-w-sm relative z-10">
        <div className="text-center mb-10">
          <h1 className="text-3xl font-bold tracking-tight">
            Build<span className="gradient-text">Leads</span>
          </h1>
          <p className="text-[#5e5e73] mt-2 text-sm">Platforma oceny potencjału klientów B2B</p>
        </div>

        <form onSubmit={handleSubmit} className="bg-[#111118] border border-[#26263a] rounded-2xl p-8">
          <h2 className="text-lg font-semibold text-[#ededf0] mb-6">Zaloguj się</h2>

          {error && (
            <div className="bg-[#ef4444]/10 border border-[#ef4444]/20 text-[#ef4444] px-4 py-3 rounded-lg mb-4 text-sm">
              {error}
            </div>
          )}

          <div className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-[#9494a8] mb-1.5 uppercase tracking-wider">Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-4 py-2.5 bg-[#0a0a0f] border border-[#26263a] rounded-lg text-[#ededf0] placeholder-[#5e5e73] focus:outline-none focus:ring-2 focus:ring-[#6366f1]/50 focus:border-[#6366f1]/50"
                placeholder="admin@buildleads.pl"
                required
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-[#9494a8] mb-1.5 uppercase tracking-wider">Hasło</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-4 py-2.5 bg-[#0a0a0f] border border-[#26263a] rounded-lg text-[#ededf0] placeholder-[#5e5e73] focus:outline-none focus:ring-2 focus:ring-[#6366f1]/50 focus:border-[#6366f1]/50"
                placeholder="••••••••"
                required
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full mt-6 py-2.5 px-4 bg-[#6366f1] hover:bg-[#818cf8] disabled:opacity-40 text-white font-medium rounded-lg transition-all glow-accent"
          >
            {loading ? "Logowanie..." : "Zaloguj się"}
          </button>

          <p className="mt-4 text-center text-xs text-[#5e5e73]">
            Demo: admin@buildleads.pl / admin123
          </p>
        </form>
      </div>
    </div>
  );
}
