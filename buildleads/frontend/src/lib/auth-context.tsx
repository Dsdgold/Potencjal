"use client";

import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { getMe, clearTokens, getToken } from "./api";

interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  role: string;
  tenant_id: string;
  is_active: boolean;
}

interface AuthCtx {
  user: User | null;
  loading: boolean;
  reload: () => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthCtx>({
  user: null,
  loading: true,
  reload: async () => {},
  logout: () => {},
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const reload = async () => {
    if (!getToken()) {
      setUser(null);
      setLoading(false);
      return;
    }
    const me = await getMe();
    setUser(me);
    setLoading(false);
  };

  const logout = () => {
    clearTokens();
    setUser(null);
    window.location.href = "/login";
  };

  useEffect(() => {
    reload();
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, reload, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
