"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { useEffect } from "react";

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: "🏠" },
  { href: "/dashboard?tab=watchlist", label: "Watchlist", icon: "👁" },
  { href: "/admin", label: "Admin", icon: "⚙️", adminOnly: true },
  { href: "/settings", label: "Ustawienia", icon: "🔧" },
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, user, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!isAuthenticated) router.push("/auth/login");
  }, [isAuthenticated, router]);

  if (!isAuthenticated) return null;

  const isAdmin = user?.role === "admin" || user?.role === "superadmin";

  return (
    <div className="min-h-screen bg-sig-bg">
      {/* Top navbar */}
      <nav className="border-b border-sig-border bg-sig-surface/90 backdrop-blur sticky top-0 z-50 no-print">
        <div className="max-w-7xl mx-auto px-4 h-14 flex items-center justify-between">
          <div className="flex items-center gap-6">
            <Link href="/dashboard" className="flex items-center gap-2">
              <span className="text-xl font-black text-sig-red tracking-wider">SIG</span>
              <span className="text-sm font-semibold hidden sm:block">Potencjał</span>
            </Link>
            <div className="hidden md:flex gap-1">
              {navItems.filter(n => !n.adminOnly || isAdmin).map(item => (
                <Link key={item.href} href={item.href}
                  className={`px-3 py-1.5 rounded-lg text-sm transition ${
                    pathname === item.href ? "bg-sig-red/10 text-sig-red" : "text-sig-muted hover:text-white"
                  }`}>
                  {item.icon} {item.label}
                </Link>
              ))}
            </div>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-xs text-sig-muted hidden sm:block">{user?.email}</span>
            <span className="text-xs px-2 py-0.5 rounded bg-sig-red/10 text-sig-red font-bold">{user?.role}</span>
            <button onClick={logout} className="text-sm text-sig-muted hover:text-white transition">
              Wyloguj
            </button>
          </div>
        </div>
      </nav>
      <main className="max-w-7xl mx-auto px-4 py-6">{children}</main>
    </div>
  );
}
