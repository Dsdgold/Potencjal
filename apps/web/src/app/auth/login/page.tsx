"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { authApi } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export default function LoginPage() {
  const [email, setEmail] = useState("demo@sig.pl");
  const [password, setPassword] = useState("demo1234");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  const { login } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await authApi.login(email, password);
      const user = await authApi.me(res.access_token);
      login(res.access_token, res.refresh_token, user);
      router.push("/dashboard");
    } catch (err: any) {
      setError(err.message || "Błąd logowania");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <Link href="/" className="text-3xl font-black text-sig-red tracking-wider">SIG</Link>
          <h1 className="text-xl font-bold mt-2">Zaloguj się</h1>
        </div>
        <form onSubmit={handleSubmit} className="bg-sig-card border border-sig-border rounded-2xl p-6 space-y-4">
          {error && <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3 text-sm text-red-400">{error}</div>}
          <div>
            <label className="block text-sm text-sig-muted mb-1">Email</label>
            <input type="email" value={email} onChange={e => setEmail(e.target.value)} required
              className="w-full bg-sig-surface border border-sig-border rounded-lg px-4 py-3 text-sig-text focus:border-sig-red focus:ring-1 focus:ring-sig-red outline-none transition" />
          </div>
          <div>
            <label className="block text-sm text-sig-muted mb-1">Hasło</label>
            <input type="password" value={password} onChange={e => setPassword(e.target.value)} required
              className="w-full bg-sig-surface border border-sig-border rounded-lg px-4 py-3 text-sig-text focus:border-sig-red focus:ring-1 focus:ring-sig-red outline-none transition" />
          </div>
          <button type="submit" disabled={loading}
            className="w-full bg-sig-red hover:bg-sig-red-dark disabled:opacity-50 rounded-lg py-3 font-bold text-white transition">
            {loading ? "Logowanie..." : "Zaloguj"}
          </button>
          <p className="text-center text-sm text-sig-muted">
            Nie masz konta? <Link href="/auth/register" className="text-sig-red hover:underline">Zarejestruj się</Link>
          </p>
          <p className="text-center text-xs text-sig-muted">Demo: demo@sig.pl / demo1234</p>
        </form>
      </div>
    </div>
  );
}
