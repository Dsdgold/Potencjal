"use client";

import { create } from "zustand";

interface AuthState {
  token: string | null;
  refreshToken: string | null;
  user: any | null;
  isAuthenticated: boolean;
  login: (token: string, refreshToken: string, user?: any) => void;
  logout: () => void;
  setUser: (user: any) => void;
}

export const useAuth = create<AuthState>((set) => {
  // Hydrate from localStorage
  let initial = { token: null as string | null, refreshToken: null as string | null, user: null };
  if (typeof window !== "undefined") {
    try {
      const stored = localStorage.getItem("auth");
      if (stored) initial = JSON.parse(stored);
    } catch {}
  }

  return {
    ...initial,
    isAuthenticated: !!initial.token,
    login: (token, refreshToken, user) => {
      const state = { token, refreshToken, user: user || null };
      localStorage.setItem("auth", JSON.stringify(state));
      set({ ...state, isAuthenticated: true });
    },
    logout: () => {
      localStorage.removeItem("auth");
      set({ token: null, refreshToken: null, user: null, isAuthenticated: false });
    },
    setUser: (user) => set({ user }),
  };
});
