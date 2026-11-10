/* eslint-disable react-refresh/only-export-components */
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { Navigate, Outlet, useLocation } from "react-router-dom";
import { api } from "./api";
import { clearDemoProgress } from "./demoProgress";
import type { User } from "./types";

export type AuthenticationStatus = "loading" | "authenticated" | "unauthenticated" | "error";

interface AuthContextValue {
  user: User | null;
  status: AuthenticationStatus;
  demoExpired: boolean;
  retrySession: () => Promise<void>;
  startDemo: () => Promise<void>;
  exitDemo: () => Promise<void>;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
}

interface AuthenticationState {
  user: User | null;
  status: AuthenticationStatus;
  demoExpired: boolean;
}

const AuthContext = createContext<AuthContextValue | null>(null);
let pendingSessionRequest: ReturnType<typeof api.session> | null = null;
let pendingDemoRequest: ReturnType<typeof api.startDemo> | null = null;

function requestSessionState() {
  if (pendingSessionRequest) return pendingSessionRequest;

  const request = api.session();
  pendingSessionRequest = request;
  void request.then(
    () => { if (pendingSessionRequest === request) pendingSessionRequest = null; },
    () => { if (pendingSessionRequest === request) pendingSessionRequest = null; },
  );
  return request;
}

function requestDemoSession() {
  if (pendingDemoRequest) return pendingDemoRequest;

  const request = api.startDemo();
  pendingDemoRequest = request;
  void request.then(
    () => { if (pendingDemoRequest === request) pendingDemoRequest = null; },
    () => { if (pendingDemoRequest === request) pendingDemoRequest = null; },
  );
  return request;
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [authentication, setAuthentication] = useState<AuthenticationState>({
    user: null,
    status: "loading",
    demoExpired: false,
  });
  const mountedRef = useRef(false);

  const restoreSession = useCallback(async () => {
    setAuthentication((current) => ({ ...current, status: "loading" }));
    try {
      const { user, demo_expired: demoExpired } = await requestSessionState();
      if (!mountedRef.current) return;
      setAuthentication({
        user,
        status: user ? "authenticated" : "unauthenticated",
        demoExpired,
      });
    } catch {
      if (!mountedRef.current) return;
      setAuthentication((current) => ({ ...current, status: "error" }));
    }
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    void restoreSession();
    const clear = () => setAuthentication({ user: null, status: "unauthenticated", demoExpired: false });
    const restoreAfterDemoExpiry = () => { void restoreSession(); };
    window.addEventListener("pactra:unauthenticated", clear);
    window.addEventListener("pactra:demo-expired", restoreAfterDemoExpiry);
    return () => {
      mountedRef.current = false;
      window.removeEventListener("pactra:unauthenticated", clear);
      window.removeEventListener("pactra:demo-expired", restoreAfterDemoExpiry);
    };
  }, [restoreSession]);

  const value = useMemo<AuthContextValue>(() => ({
    retrySession: restoreSession,
    status: authentication.status,
    user: authentication.user,
    demoExpired: authentication.demoExpired,
    startDemo: async () => {
      clearDemoProgress();
      const result = await requestDemoSession();
      setAuthentication({ user: result.user, status: "authenticated", demoExpired: false });
    },
    exitDemo: async () => {
      await api.exitDemo();
    },
    signIn: async (email, password) => {
      const result = await api.login(email, password);
      setAuthentication({ user: result.user, status: "authenticated", demoExpired: false });
    },
    signUp: async (email, password) => {
      const result = await api.register(email, password);
      setAuthentication({ user: result.user, status: "authenticated", demoExpired: false });
    },
    signOut: async () => {
      await api.logout();
      setAuthentication({ user: null, status: "unauthenticated", demoExpired: false });
    },
  }), [authentication, restoreSession]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used inside AuthProvider");
  return value;
}

export function ProtectedRoute() {
  const { demoExpired, retrySession, status, user } = useAuth();
  const location = useLocation();
  if (status === "loading") return <SessionLoadingState />;
  if (status === "error") return <SessionErrorState onRetry={retrySession} />;
  if (!user) return <Navigate replace state={{ from: location.pathname }} to={demoExpired ? "/" : "/sign-in"} />;
  return <Outlet />;
}

export function GuestRoute() {
  const { retrySession, status, user } = useAuth();
  if (status === "loading") return <SessionLoadingState />;
  if (status === "error") return <SessionErrorState onRetry={retrySession} />;
  return user ? <Navigate replace to="/app" /> : <Outlet />;
}

export function NormalAccountRoute() {
  const { user } = useAuth();
  return user?.is_demo ? <Navigate replace to="/app" /> : <Outlet />;
}

function SessionLoadingState() {
  return (
    <div className="grid min-h-screen place-items-center bg-canvas px-6 text-center text-ink-950" role="status">
      <div>
        <span aria-hidden="true" className="mx-auto block h-2.5 w-2.5 rounded-full bg-pactra-600" />
        <p className="mt-3 text-sm text-ink-500">Checking your Pactra session</p>
      </div>
    </div>
  );
}

function SessionErrorState({ onRetry }: { onRetry: () => Promise<void> }) {
  return (
    <div className="grid min-h-screen place-items-center bg-canvas px-6 text-center text-ink-950">
      <div className="max-w-sm">
        <p className="text-lg font-medium">Session check unavailable</p>
        <p className="mt-2 text-sm leading-6 text-ink-500">Pactra could not verify your session. Your account has not been signed out.</p>
        <button className="action-secondary mt-5" onClick={() => void onRetry()} type="button">Retry session</button>
      </div>
    </div>
  );
}
