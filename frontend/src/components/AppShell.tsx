import {
  Bot,
  CircleDollarSign,
  CreditCard,
  FileText,
  LayoutDashboard,
  LogOut,
  Menu,
  Settings,
  ShieldCheck,
  SlidersHorizontal,
  X,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth";
import { BrandMark } from "./Brand";
import { DemoBanner } from "./DemoBanner";

const navSections = [
  {
    label: "Workspace",
    items: [
      { to: "/app", label: "Overview", icon: LayoutDashboard, end: true },
      { to: "/app/assistant", label: "Assistant", icon: Bot },
    ],
  },
  {
    label: "Payments",
    items: [
      { to: "/app/payments/new", label: "New payment", icon: CreditCard },
      { to: "/app/approvals", label: "Approvals", icon: ShieldCheck },
      { to: "/app/transactions", label: "Transactions", icon: FileText },
    ],
  },
  {
    label: "Controls",
    items: [
      { to: "/app/policies", label: "Policies", icon: SlidersHorizontal },
      { to: "/app/wallet", label: "Wallet", icon: CircleDollarSign },
      { to: "/app/settings", label: "Settings", icon: Settings },
    ],
  },
];

function WorkspaceNavigation({ isDemo, onNavigate }: { isDemo: boolean; onNavigate?: () => void }) {
  return <nav aria-label="Workspace navigation" className="space-y-6">
    {navSections.map((section) => <div key={section.label}>
      <p className="px-3 text-xs text-ink-400">{section.label}</p>
      <div className="mt-2 space-y-1">{section.items.filter((item) => !(isDemo && item.to.startsWith("/app/settings"))).map(({ to, label, icon: Icon, end }) => <NavLink end={end} key={to} onClick={onNavigate} to={to} className={({ isActive }) => `flex h-11 items-center gap-3 rounded-lg border-l-2 px-3 text-sm transition-colors duration-150 ${isActive ? "border-pactra-600 bg-surface-raised text-ink-950" : "border-transparent text-ink-500 hover:bg-surface hover:text-ink-800"}`}><Icon aria-hidden="true" className="h-4 w-4 shrink-0" strokeWidth={1.5} />{label}</NavLink>)}</div>
    </div>)}
  </nav>;
}

function SidebarFooter({ error, isDemo, label, onSignOut }: { error: string; isDemo: boolean; label?: string; onSignOut: () => void }) {
  return (
    <div className="shrink-0 border-t border-line pt-4" data-testid="sidebar-footer">
      <p className="truncate px-3 text-xs text-ink-500">{label}</p>
      {error ? <p aria-live="polite" className="mt-2 px-3 text-xs leading-5 text-negative">{error}</p> : null}
      <button className="mt-2 flex h-11 w-full items-center gap-3 rounded-lg px-3 text-sm text-ink-500 transition-colors hover:bg-surface hover:text-ink-950" onClick={onSignOut} type="button"><LogOut aria-hidden="true" className="h-4 w-4" />{isDemo ? "Exit demo" : "Sign out"}</button>
    </div>
  );
}

export function AppShell() {
  const { exitDemo, user, signOut } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [logoutError, setLogoutError] = useState("");
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const mobileMenuButtonRef = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    let robots = document.head.querySelector<HTMLMetaElement>('meta[name="robots"]');
    const created = !robots;
    const previous = robots?.content ?? "";
    if (!robots) {
      robots = document.createElement("meta");
      robots.name = "robots";
      document.head.appendChild(robots);
    }
    robots.content = "noindex, nofollow";
    return () => {
      if (created) robots?.remove();
      else if (robots) robots.content = previous;
    };
  }, []);
  useEffect(() => { setMobileMenuOpen(false); }, [location.pathname]);
  useEffect(() => {
    if (!mobileMenuOpen) return;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      setMobileMenuOpen(false);
      mobileMenuButtonRef.current?.focus();
    };
    document.addEventListener("keydown", closeOnEscape);
    return () => document.removeEventListener("keydown", closeOnEscape);
  }, [mobileMenuOpen]);
  async function logout() {
    setLogoutError("");
    try {
      if (user?.is_demo) {
        await exitDemo();
        window.location.assign("/");
        return;
      }
      await signOut();
      navigate("/sign-in", { replace: true });
    } catch {
      setLogoutError(user?.is_demo ? "Exit failed. Try again." : "Sign out failed. Try again.");
    }
  }
  return <div className="grid h-dvh min-h-0 overflow-hidden bg-canvas text-ink-950 lg:grid-cols-[272px_minmax(0,1fr)]">
    <a className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-pactra-600 focus:px-4 focus:py-2 focus:text-white" href="#main-content">Skip to content</a>
    <aside className="z-30 hidden h-dvh min-h-0 flex-col border-r border-line bg-canvas-deep px-4 py-5 lg:flex" data-testid="desktop-sidebar">
      <NavLink className="flex min-h-11 shrink-0 items-center gap-3 px-2" to="/app"><BrandMark /><span><span className="block text-[17px] font-medium text-ink-950">Pactra</span><span className="block text-xs text-ink-500">Payment control room</span></span></NavLink>
      <div className="mt-6 min-h-0 flex-1 overflow-y-auto overscroll-contain pr-1" data-testid="sidebar-navigation-scroll"><WorkspaceNavigation isDemo={Boolean(user?.is_demo)} /></div>
      <SidebarFooter error={logoutError} isDemo={Boolean(user?.is_demo)} label={user?.display_name ?? user?.email} onSignOut={() => void logout()} />
    </aside>
    <div className="flex h-dvh min-h-0 min-w-0 flex-col overflow-hidden">
      <header className="relative z-30 shrink-0 border-b border-line bg-canvas/95 backdrop-blur lg:hidden">
        <div className="flex h-[60px] items-center justify-between px-4"><NavLink className="flex min-h-11 items-center gap-2.5 font-medium" to="/app"><BrandMark className="h-8 w-8" />Pactra</NavLink><button aria-controls="workspace-mobile-navigation" aria-expanded={mobileMenuOpen} aria-label={mobileMenuOpen ? "Close navigation" : "Open navigation"} className="icon-button" onClick={() => setMobileMenuOpen((open) => !open)} ref={mobileMenuButtonRef} type="button">{mobileMenuOpen ? <X aria-hidden="true" className="h-4 w-4" /> : <Menu aria-hidden="true" className="h-4 w-4" />}</button></div>
        {mobileMenuOpen ? <div className="mobile-nav-panel absolute inset-x-0 top-full flex h-[calc(100dvh-60px)] min-h-0 flex-col border-t border-line bg-canvas-deep px-4 py-5 shadow-float" id="workspace-mobile-navigation"><div className="min-h-0 flex-1 overflow-y-auto overscroll-contain pr-1" data-testid="mobile-navigation-scroll"><WorkspaceNavigation isDemo={Boolean(user?.is_demo)} onNavigate={() => setMobileMenuOpen(false)} /></div><SidebarFooter error={logoutError} isDemo={Boolean(user?.is_demo)} label={user?.display_name ?? user?.email} onSignOut={() => void logout()} /></div> : null}
      </header>
      {user?.is_demo ? <DemoBanner /> : <div className="shrink-0 border-b border-line bg-canvas-deep px-4 py-2 text-center text-xs text-warning-dark sm:px-6">Sandbox funds only · No real money moves</div>}
      <main className="min-h-0 flex-1 overflow-y-auto overscroll-contain" data-testid="main-content-scroll" id="main-content" tabIndex={-1}><div className="pactra-enter mx-auto max-w-[1560px] px-4 py-6 sm:px-6 lg:px-8 lg:py-8"><Outlet /></div></main>
    </div>
  </div>;
}
