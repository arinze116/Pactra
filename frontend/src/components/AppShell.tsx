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
import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth";
import { BrandMark } from "./Brand";

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

function WorkspaceNavigation({ onNavigate }: { onNavigate?: () => void }) {
  return <nav aria-label="Workspace navigation" className="space-y-6">
    {navSections.map((section) => <div key={section.label}>
      <p className="px-3 text-xs text-ink-400">{section.label}</p>
      <div className="mt-2 space-y-1">{section.items.map(({ to, label, icon: Icon, end }) => <NavLink end={end} key={to} onClick={onNavigate} to={to} className={({ isActive }) => `flex h-9 items-center gap-3 rounded-lg border-l-2 px-3 text-sm transition-colors duration-150 ${isActive ? "border-pactra-600 bg-surface-raised text-ink-950" : "border-transparent text-ink-500 hover:bg-surface hover:text-ink-800"}`}><Icon className="h-4 w-4 shrink-0" strokeWidth={1.5} />{label}</NavLink>)}</div>
    </div>)}
  </nav>;
}

export function AppShell() {
  const { user, signOut } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
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
  async function logout() {
    await signOut();
    navigate("/sign-in", { replace: true });
  }
  return <div className="min-h-screen bg-canvas text-ink-950">
    <a className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-pactra-600 focus:px-4 focus:py-2 focus:text-white" href="#main-content">Skip to content</a>
    <aside className="fixed inset-y-0 left-0 z-30 hidden w-[272px] flex-col border-r border-line bg-canvas-deep px-4 py-5 lg:flex">
      <NavLink className="flex items-center gap-3 px-2" to="/app"><BrandMark /><span><span className="block text-[17px] font-medium text-ink-950">Pactra</span><span className="block text-xs text-ink-500">Payment control room</span></span></NavLink>
      <div className="mt-8"><WorkspaceNavigation /></div>
      <div className="mt-auto border-t border-line pt-4"><p className="truncate px-3 text-xs text-ink-500">{user?.email}</p><button className="mt-2 flex h-9 w-full items-center gap-3 rounded-lg px-3 text-sm text-ink-500 transition-colors hover:bg-surface hover:text-ink-950" onClick={() => void logout()} type="button"><LogOut className="h-4 w-4" />Sign out</button></div>
    </aside>
    <div className="min-w-0 lg:pl-[272px]">
      <header className="sticky top-0 z-30 border-b border-line bg-canvas/95 backdrop-blur lg:hidden">
        <div className="flex h-[60px] items-center justify-between px-4"><NavLink className="flex items-center gap-2.5 font-medium" to="/app"><BrandMark className="h-8 w-8" />Pactra</NavLink><button aria-expanded={mobileMenuOpen} aria-label={mobileMenuOpen ? "Close navigation" : "Open navigation"} className="icon-button" onClick={() => setMobileMenuOpen((open) => !open)} type="button">{mobileMenuOpen ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}</button></div>
        {mobileMenuOpen ? <div className="mobile-nav-panel border-t border-line bg-canvas-deep px-4 py-5"><WorkspaceNavigation onNavigate={() => setMobileMenuOpen(false)} /><div className="mt-5 border-t border-line pt-4"><p className="truncate px-3 text-xs text-ink-500">{user?.email}</p><button className="mt-2 flex h-9 w-full items-center gap-3 rounded-lg px-3 text-sm text-ink-500" onClick={() => void logout()} type="button"><LogOut className="h-4 w-4" />Sign out</button></div></div> : null}
      </header>
      <div className="border-b border-line bg-canvas-deep px-4 py-2 text-center text-xs text-warning-dark sm:px-6">Sandbox funds only · No real money moves</div>
      <main className="pactra-enter mx-auto max-w-[1560px] px-4 py-6 sm:px-6 lg:px-8 lg:py-8" id="main-content"><Outlet /></main>
    </div>
  </div>;
}
