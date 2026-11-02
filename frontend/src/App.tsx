import { useCallback, useEffect, useState } from "react";
import { Activity, Bell, ShieldCheck, X } from "lucide-react";
import { api } from "./api";
import { Chat } from "./components/Chat";
import { Dashboard } from "./components/Dashboard";
import { PolicyPanel } from "./components/PolicyPanel";
import type { Policy, SpendSummary, Transaction } from "./types";

export default function App() {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [summaries, setSummaries] = useState<SpendSummary[]>([]);
  const [policy, setPolicy] = useState<Policy | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refreshData = useCallback(async (showLoader = false) => {
    if (showLoader) setLoading(true);
    try {
      const [nextTransactions, nextSummaries, nextPolicy] = await Promise.all([
        api.transactions(),
        api.spendSummary(),
        api.policy(),
      ]);
      setTransactions(nextTransactions);
      setSummaries(nextSummaries);
      setPolicy(nextPolicy);
      setError(null);
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "The governance dashboard could not be loaded.",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refreshData(true);
    const interval = window.setInterval(() => void refreshData(), 10_000);
    return () => window.clearInterval(interval);
  }, [refreshData]);

  return (
    <div className="min-h-screen bg-ink-950 bg-page-glow text-slate-200">
      <header className="border-b border-white/[0.06] bg-ink-950/80 px-4 backdrop-blur-xl sm:px-6 lg:px-8">
        <div className="mx-auto flex h-[72px] max-w-[1800px] items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="relative grid h-10 w-10 place-items-center overflow-hidden rounded-xl bg-gradient-to-br from-pactra-400 to-pactra-600 text-lg font-black text-ink-950 shadow-[0_8px_30px_rgba(24,201,151,0.22)]">
              P
              <span className="absolute right-1 top-1 h-1.5 w-1.5 rounded-full bg-white/80" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-base font-bold tracking-[0.2em] text-white">PACTRA</h1>
                <span className="rounded bg-pactra-400/10 px-1.5 py-0.5 text-[8px] font-bold uppercase tracking-[0.13em] text-pactra-300 ring-1 ring-inset ring-pactra-300/15">
                  Sandbox
                </span>
              </div>
              <p className="mt-0.5 text-[10px] font-medium tracking-wide text-slate-600">
                AI payment governance
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 sm:gap-3">
            <div className="hidden items-center gap-2 rounded-full border border-white/[0.06] bg-white/[0.025] px-3 py-1.5 text-[10px] font-medium text-slate-500 sm:flex">
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-pactra-400 opacity-50" />
                <span className="relative inline-flex h-2 w-2 rounded-full bg-pactra-400" />
              </span>
              Policy engine live
            </div>
            <button
              aria-label="Notifications"
              className="relative grid h-9 w-9 place-items-center rounded-xl border border-white/[0.06] bg-white/[0.025] text-slate-500 transition hover:text-white"
              type="button"
            >
              <Bell className="h-4 w-4" aria-hidden="true" />
              {transactions.some((item) => item.status === "pending_approval") ? (
                <span className="absolute right-2 top-2 h-1.5 w-1.5 rounded-full bg-amber-300 ring-2 ring-ink-950" />
              ) : null}
            </button>
            <div className="grid h-9 w-9 place-items-center rounded-xl bg-gradient-to-br from-violet-400/30 to-sky-400/20 text-xs font-bold text-violet-100 ring-1 ring-inset ring-white/10">
              MR
            </div>
          </div>
        </div>
      </header>

      <PolicyPanel loading={loading} policy={policy} summaries={summaries} />

      {error ? (
        <div className="fixed left-1/2 top-20 z-50 flex w-[calc(100%-2rem)] max-w-xl -translate-x-1/2 items-center gap-3 rounded-xl border border-rose-300/15 bg-rose-950/90 px-4 py-3 text-xs text-rose-100 shadow-2xl backdrop-blur-xl">
          <Activity className="h-4 w-4 shrink-0 text-rose-300" aria-hidden="true" />
          <span className="flex-1">{error}</span>
          <button
            aria-label="Dismiss error"
            className="text-rose-300/70 transition hover:text-white"
            onClick={() => setError(null)}
            type="button"
          >
            <X className="h-4 w-4" aria-hidden="true" />
          </button>
        </div>
      ) : null}

      <main className="mx-auto min-w-0 max-w-[1800px] px-4 py-4 sm:px-6 lg:px-8 lg:py-5">
        <div className="grid min-w-0 gap-4 lg:grid-cols-2">
          <Chat onTransactionCreated={() => refreshData()} />
          <Dashboard
            loading={loading}
            onError={setError}
            onRefresh={() => refreshData(true)}
            transactions={transactions}
          />
        </div>
        <footer className="flex flex-col items-center justify-between gap-2 px-1 pb-2 pt-4 text-[9px] uppercase tracking-[0.14em] text-slate-700 sm:flex-row">
          <span className="flex items-center gap-1.5">
            <ShieldCheck className="h-3 w-3" aria-hidden="true" />
            Policy enforced before every transaction
          </span>
          <span>PayPal Sandbox · Gemini 2.0 Flash</span>
        </footer>
      </main>
    </div>
  );
}
