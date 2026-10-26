import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import { api, ApiError, tokenStore } from "../lib/api";
import type { User } from "../lib/types";

interface AuthValue {
  user: User | null;
  ready: boolean;
  loginOpen: boolean;
  /** Opens the login sheet; `then` runs once the user has logged in. */
  requireLogin: (then?: () => void) => void;
  closeLogin: () => void;
  completeLogin: (token: string, user: User) => void;
  setUser: (user: User) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);
  const [loginOpen, setLoginOpen] = useState(false);
  const afterLogin = useRef<(() => void) | undefined>(undefined);

  useEffect(() => {
    if (!tokenStore.get()) {
      setReady(true);
      return;
    }
    api
      .me()
      .then(setUser)
      .catch((err) => {
        if (err instanceof ApiError && err.status === 401) tokenStore.set(null);
      })
      .finally(() => setReady(true));
  }, []);

  const requireLogin = useCallback(
    (then?: () => void) => {
      if (user) {
        then?.();
        return;
      }
      afterLogin.current = then;
      setLoginOpen(true);
    },
    [user],
  );

  const completeLogin = useCallback((token: string, loggedIn: User) => {
    tokenStore.set(token);
    setUser(loggedIn);
    setLoginOpen(false);
    const then = afterLogin.current;
    afterLogin.current = undefined;
    then?.();
  }, []);

  const logout = useCallback(() => {
    tokenStore.set(null);
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user,
        ready,
        loginOpen,
        requireLogin,
        closeLogin: () => setLoginOpen(false),
        completeLogin,
        setUser,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthValue {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used inside <AuthProvider>");
  return value;
}
