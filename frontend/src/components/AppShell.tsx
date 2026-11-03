import {
  Bot,
  CircleDollarSign,
  CreditCard,
  FileText,
  LayoutDashboard,
  LogOut,
  Settings,
  ShieldCheck,
  SlidersHorizontal,
} from "lucide-react";
import { useEffect } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../auth";

const nav = [
  { to: "/app", label: "Overview", icon: LayoutDashboard, end: true },
  { to: "/app/payments/new", label: "New payment", icon: CreditCard },
  { to: "/app/assistant", label: "Assistant", icon: Bot },
  { to: "/app/approvals", label: "Approvals", icon: ShieldCheck },
  { to: "/app/transactions", label: "Transactions", icon: FileText },
  { to: "/app/policies", label: "Policies", icon: SlidersHorizontal },
  { to: "/app/wallet", label: "Wallet", icon: CircleDollarSign },
  { to: "/app/settings", label: "Settings", icon: Settings },
];

export function AppShell() {
  const { user, signOut } = useAuth();
  const navigate = useNavigate();
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
  async function logout() {
    await signOut();
    navigate("/sign-in", { replace: true });
  }
  return <div className="min-h-screen bg-canvas text-ink-950">
    <a className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-pactra-600 focus:px-4 focus:py-2 focus:text-canvas" href="#main-content">Skip to content</a>
    <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 flex-col border-r border-line bg-[#090c09] px-4 py-5 lg:flex">
      <NavLink className="flex items-center gap-3 px-2" to="/app"><span className="grid h-9 w-9 place-items-center rounded-lg bg-pactra-600 text-canvas"><ShieldCheck className="h-[18px] w-[18px]" strokeWidth={1.75} /></span><span><span className="block text-[17px] font-medium text-ink-950">Pactra</span><span className="block text-xs text-ink-500">Policy control room</span></span></NavLink>
      <div className="mt-8 px-3 text-xs text-ink-500">Workspace</div>
      <nav className="mt-2 space-y-1" aria-label="Workspace navigation">{nav.map(({ to, label, icon: Icon, end }) => <NavLink end={end} key={to} to={to} className={({ isActive }) => `flex h-9 items-center gap-3 rounded-lg border-l-2 px-3 text-sm transition-colors duration-150 ${isActive ? "border-pactra-600 bg-surface-raised text-ink-950" : "border-transparent text-ink-500 hover:bg-surface hover:text-ink-800"}`}><Icon className="h-4 w-4" strokeWidth={1.5} />{label}</NavLink>)}</nav>
      <div className="mt-auto border-t border-line pt-4"><p className="truncate px-3 text-xs text-ink-500">{user?.email}</p><button className="mt-2 flex h-9 w-full items-center gap-3 rounded-lg px-3 text-sm text-ink-500 transition-colors hover:bg-surface hover:text-ink-950" onClick={() => void logout()} type="button"><LogOut className="h-4 w-4" />Sign out</button></div>
    </aside>
    <div className="min-w-0 lg:pl-64">
      <header className="sticky top-0 z-20 border-b border-line bg-canvas/95 backdrop-blur lg:hidden"><div className="flex h-14 items-center justify-between px-4"><NavLink className="flex items-center gap-2 font-medium" to="/app"><span className="grid h-7 w-7 place-items-center rounded-md bg-pactra-600 text-canvas"><ShieldCheck className="h-4 w-4" /></span>Pactra</NavLink><span className="text-xs text-ink-500">Sandbox</span></div><nav className="flex gap-1 overflow-x-auto border-t border-line px-3 py-2">{nav.map(({ to, label }) => <NavLink key={to} to={to} className={({ isActive }) => `shrink-0 rounded-lg px-3 py-2 text-xs ${isActive ? "bg-surface-raised text-ink-950" : "text-ink-500"}`}>{label}</NavLink>)}</nav></header>
      <div className="border-b border-line bg-[#101510] px-4 py-2 text-center text-xs text-warning-dark sm:px-6">Sandbox funds only · No real money moves</div>
      <main className="pactra-enter mx-auto max-w-[1560px] px-4 py-6 sm:px-6 lg:px-8 lg:py-8" id="main-content"><Outlet /></main>
    </div>
  </div>;
}
