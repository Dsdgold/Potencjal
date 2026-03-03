"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth-context";

const nav = [
  { href: "/dashboard", label: "Dashboard", icon: "📊" },
  { href: "/leads", label: "Leady", icon: "👥" },
];

export function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  return (
    <aside className="w-64 bg-slate-800 border-r border-slate-700 flex flex-col min-h-screen">
      <div className="p-6 border-b border-slate-700">
        <h1 className="text-2xl font-bold text-white tracking-tight">
          Build<span className="text-blue-400">Leads</span>
        </h1>
      </div>

      <nav className="flex-1 p-4 space-y-1">
        {nav.map((item) => {
          const active = pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                active
                  ? "bg-blue-600/20 text-blue-400"
                  : "text-slate-300 hover:bg-slate-700/50 hover:text-white"
              }`}
            >
              <span className="text-lg">{item.icon}</span>
              {item.label}
            </Link>
          );
        })}
      </nav>

      {user && (
        <div className="p-4 border-t border-slate-700">
          <div className="flex items-center gap-3 px-2 mb-3">
            <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center text-white text-sm font-bold">
              {user.first_name?.[0] || user.email[0].toUpperCase()}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-white truncate">
                {user.first_name} {user.last_name}
              </p>
              <p className="text-xs text-slate-400 truncate">{user.role}</p>
            </div>
          </div>
          <button
            onClick={logout}
            className="w-full px-4 py-2 text-sm text-slate-400 hover:text-white hover:bg-slate-700/50 rounded-lg transition-colors text-left"
          >
            Wyloguj się
          </button>
        </div>
      )}
    </aside>
  );
}
