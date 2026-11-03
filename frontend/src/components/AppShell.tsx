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
    <a className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-white focus:px-4 focus:py-2" href="#main-content">Skip to content</a>
    <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 flex-col border-r border-white/10 bg-ink-950 px-4 py-5 text-white lg:flex">
      <NavLink className="flex items-center gap-3 px-2" to="/app"><span className="grid h-9 w-9 place-items-center rounded-lg border border-white/10 bg-white/[0.06]"><ShieldCheck className="h-[18px] w-[18px] text-pactra-300" strokeWidth={1.5} /></span><span><span className="block text-[17px] font-medium">Pactra</span><span className="block text-xs text-white/45">Sandbox operations</span></span></NavLink>
      <nav className="mt-8 space-y-1" aria-label="Workspace navigation">{nav.map(({ to, label, icon: Icon, end }) => <NavLink end={end} key={to} to={to} className={({ isActive }) => `flex h-9 items-center gap-3 rounded-lg px-3 text-sm transition-colors duration-150 ${isActive ? "bg-white/10 text-white" : "text-white/55 hover:bg-white/[0.06] hover:text-white"}`}><Icon className="h-4 w-4" strokeWidth={1.5} />{label}</NavLink>)}</nav>
      <div className="mt-auto border-t border-white/10 pt-4"><p className="truncate px-2 text-xs text-white/50">{user?.email}</p><button className="mt-2 flex h-9 w-full items-center gap-3 rounded-lg px-3 text-sm text-white/55 hover:bg-white/[0.06] hover:text-white" onClick={() => void logout()} type="button"><LogOut className="h-4 w-4" />Sign out</button></div>
    </aside>
    <div className="min-w-0 lg:pl-64">
      <header className="sticky top-0 z-20 border-b border-line bg-canvas/95 lg:hidden"><div className="flex h-14 items-center justify-between px-4"><NavLink className="flex items-center gap-2 font-medium" to="/app"><ShieldCheck className="h-5 w-5" />Pactra</NavLink><span className="text-xs text-ink-500">Sandbox only</span></div><nav className="flex gap-1 overflow-x-auto border-t border-line px-3 py-2">{nav.map(({ to, label }) => <NavLink key={to} to={to} className={({ isActive }) => `shrink-0 rounded-lg px-3 py-2 text-xs ${isActive ? "bg-white text-ink-950" : "text-ink-500"}`}>{label}</NavLink>)}</nav></header>
      <div className="border-b border-amber-200 bg-amber-50 px-4 py-2 text-center text-xs text-amber-900 sm:px-6">Sandbox funds only. No real money is moved.</div>
      <main className="pactra-enter mx-auto max-w-[1560px] px-4 py-6 sm:px-6 lg:px-8 lg:py-8" id="main-content"><Outlet /></main>
    </div>
  </div>;
}
