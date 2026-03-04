"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth-context";

const nav = [
  { href: "/dashboard", label: "Dashboard", icon: (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6A2.25 2.25 0 016 3.75h2.25A2.25 2.25 0 0110.5 6v2.25a2.25 2.25 0 01-2.25 2.25H6a2.25 2.25 0 01-2.25-2.25V6zM3.75 15.75A2.25 2.25 0 016 13.5h2.25a2.25 2.25 0 012.25 2.25V18a2.25 2.25 0 01-2.25 2.25H6A2.25 2.25 0 013.75 18v-2.25zM13.5 6a2.25 2.25 0 012.25-2.25H18A2.25 2.25 0 0120.25 6v2.25A2.25 2.25 0 0118 10.5h-2.25a2.25 2.25 0 01-2.25-2.25V6zM13.5 15.75a2.25 2.25 0 012.25-2.25H18a2.25 2.25 0 012.25 2.25V18A2.25 2.25 0 0118 20.25h-2.25A2.25 2.25 0 0113.5 18v-2.25z" />
    </svg>
  )},
  { href: "/leads", label: "Leady", icon: (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M18 18.72a9.094 9.094 0 003.741-.479 3 3 0 00-4.682-2.72m.94 3.198l.001.031c0 .225-.012.447-.037.666A11.944 11.944 0 0112 21c-2.17 0-4.207-.576-5.963-1.584A6.062 6.062 0 016 18.719m12 0a5.971 5.971 0 00-.941-3.197m0 0A5.995 5.995 0 0012 12.75a5.995 5.995 0 00-5.058 2.772m0 0a3 3 0 00-4.681 2.72 8.986 8.986 0 003.74.477m.94-3.197a5.971 5.971 0 00-.94 3.197M15 6.75a3 3 0 11-6 0 3 3 0 016 0zm6 3a2.25 2.25 0 11-4.5 0 2.25 2.25 0 014.5 0zm-13.5 0a2.25 2.25 0 11-4.5 0 2.25 2.25 0 014.5 0z" />
    </svg>
  )},
];

export function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  return (
    <aside className="w-64 bg-[#0a1014] border-r border-[rgba(14,165,233,0.06)] flex flex-col min-h-screen relative">
      {/* Gradient glow top */}
      <div className="absolute top-0 left-0 w-full h-32 bg-gradient-to-b from-[#0ea5e9]/4 to-transparent pointer-events-none" />
      <div className="absolute top-0 right-0 w-32 h-32 bg-[#a855f7]/3 rounded-full blur-[60px] pointer-events-none" />

      {/* Logo */}
      <div className="px-6 py-6 border-b border-[rgba(14,165,233,0.06)] relative">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-[#0ea5e9] to-[#38bdf8] flex items-center justify-center shadow-lg shadow-[#0ea5e9]/20">
            <span className="text-white font-black text-sm">BL</span>
          </div>
          <div>
            <h1 className="text-base font-bold tracking-tight text-[#e8edf2]">
              Build<span className="gradient-text">Leads</span>
            </h1>
            <p className="text-[9px] text-[#455566] tracking-[0.2em] uppercase font-medium">Lead Intelligence</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-5 space-y-1">
        <p className="px-3 mb-3 text-[10px] text-[#455566] uppercase tracking-[0.15em] font-semibold">Menu</p>
        {nav.map((item) => {
          const active = pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-[13px] font-medium transition-all duration-200 ${
                active
                  ? "bg-gradient-to-r from-[#0ea5e9]/15 to-[#0ea5e9]/5 text-[#7dd3fc] border border-[#0ea5e9]/20 shadow-sm shadow-[#0ea5e9]/5"
                  : "text-[#7b8fa0] hover:bg-[#162028] hover:text-[#e8edf2] border border-transparent"
              }`}
            >
              <span className={active ? "text-[#0ea5e9]" : "text-[#455566]"}>{item.icon}</span>
              {item.label}
              {active && <div className="ml-auto w-1.5 h-1.5 rounded-full bg-[#0ea5e9] shadow-sm shadow-[#0ea5e9]/50" />}
            </Link>
          );
        })}
      </nav>

      {/* Stats mini */}
      <div className="px-4 py-3 mx-3 mb-3 rounded-xl bg-[#0f171e] border border-[rgba(14,165,233,0.06)]">
        <p className="text-[10px] text-[#455566] uppercase tracking-wider font-medium mb-2">Status</p>
        <div className="flex items-center gap-2 text-xs">
          <span className="w-2 h-2 rounded-full bg-[#22c55e] shadow-sm shadow-[#22c55e]/50 pulse-dot" />
          <span className="text-[#7b8fa0]">System aktywny</span>
        </div>
      </div>

      {/* User section */}
      {user && (
        <div className="px-4 py-4 border-t border-[rgba(14,165,233,0.06)]">
          <div className="flex items-center gap-3 px-1 mb-3">
            <div className="w-9 h-9 bg-gradient-to-br from-[#0ea5e9] to-[#a855f7] rounded-xl flex items-center justify-center text-white text-xs font-bold shadow-lg shadow-[#0ea5e9]/15">
              {user.first_name?.[0] || user.email[0].toUpperCase()}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-[13px] font-semibold text-[#e8edf2] truncate">
                {user.first_name} {user.last_name}
              </p>
              <p className="text-[10px] text-[#455566] truncate uppercase tracking-wider">{user.role}</p>
            </div>
          </div>
          <button
            onClick={logout}
            className="w-full px-3 py-2 text-[12px] text-[#455566] hover:text-[#ef4444] hover:bg-[#ef4444]/5 rounded-xl transition-all text-left font-medium"
          >
            Wyloguj sie
          </button>
        </div>
      )}
    </aside>
  );
}
