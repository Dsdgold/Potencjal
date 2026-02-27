"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { authApi } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export default function RegisterPage() {
  const [form, setForm] = useState({ email: "", password: "", full_name: "", org_name: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  const { login } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await authApi.register(form);
      const user = await authApi.me(res.access_token);
      login(res.access_token, res.refresh_token, user);
      router.push("/dashboard");
    } catch (err: any) {
      setError(err.message || "Błąd rejestracji");
    } finally {
      setLoading(false);
    }
  };

  const set = (key: string) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm({ ...form, [key]: e.target.value });

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <Link href="/" className="text-3xl font-black text-sig-red tracking-wider">SIG</Link>
          <h1 className="text-xl font-bold mt-2">Załóż konto</h1>
        </div>
        <form onSubmit={handleSubmit} className="bg-sig-card border border-sig-border rounded-2xl p-6 space-y-4">
          {error && <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3 text-sm text-red-400">{error}</div>}
          <div>
            <label className="block text-sm text-sig-muted mb-1">Imię i nazwisko</label>
            <input type="text" value={form.full_name} onChange={set("full_name")} required
              className="w-full bg-sig-surface border border-sig-border rounded-lg px-4 py-3 focus:border-sig-red outline-none transition" />
          </div>
          <div>
            <label className="block text-sm text-sig-muted mb-1">Nazwa organizacji</label>
            <input type="text" value={form.org_name} onChange={set("org_name")} required
              className="w-full bg-sig-surface border border-sig-border rounded-lg px-4 py-3 focus:border-sig-red outline-none transition" />
          </div>
          <div>
            <label className="block text-sm text-sig-muted mb-1">Email</label>
            <input type="email" value={form.email} onChange={set("email")} required
              className="w-full bg-sig-surface border border-sig-border rounded-lg px-4 py-3 focus:border-sig-red outline-none transition" />
          </div>
          <div>
            <label className="block text-sm text-sig-muted mb-1">Hasło (min. 8 znaków)</label>
            <input type="password" value={form.password} onChange={set("password")} required minLength={8}
              className="w-full bg-sig-surface border border-sig-border rounded-lg px-4 py-3 focus:border-sig-red outline-none transition" />
          </div>
          <button type="submit" disabled={loading}
            className="w-full bg-sig-red hover:bg-sig-red-dark disabled:opacity-50 rounded-lg py-3 font-bold text-white transition">
            {loading ? "Tworzenie konta..." : "Zarejestruj"}
          </button>
          <p className="text-center text-sm text-sig-muted">
            Masz konto? <Link href="/auth/login" className="text-sig-red hover:underline">Zaloguj się</Link>
          </p>
        </form>
      </div>
    </div>
  );
}
