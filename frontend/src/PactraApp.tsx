import { useCallback, useEffect, useState } from "react";
import {
  Activity,
  Command,
  LayoutDashboard,
  ReceiptText,
  SlidersHorizontal,
  ShieldCheck,
  X,
} from "lucide-react";
import { api } from "./api";
import { PaymentAgent } from "./components/PaymentAgent";
import { PolicyOverview } from "./components/PolicyOverview";
import { TransactionLedger } from "./components/TransactionLedger";
import type { Policy, SpendSummary, Transaction } from "./types";

const navigation = [
  { label: "Overview", href: "#overview", icon: LayoutDashboard },
  { label: "New payment", href: "#agent", icon: Command },
  { label: "Decisions", href: "#transactions", icon: ReceiptText },
  { label: "Policy", href: "#policy", icon: SlidersHorizontal },
];

const today = new Intl.DateTimeFormat("en-NG", {
  weekday: "long",
  month: "long",
  day: "numeric",
}).format(new Date());

export default function PactraApp() {
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

  const pendingCount = transactions.filter(
    (transaction) => transaction.status === "pending_approval",
  ).length;

  return (
    <div className="min-h-screen bg-canvas text-ink-950">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-60 flex-col border-r border-white/10 bg-ink-950 px-4 py-5 text-white lg:flex">
        <div className="flex items-center gap-3 px-2">
          <span className="grid h-9 w-9 place-items-center rounded-lg border border-white/10 bg-white/[0.06] text-pactra-300">
            <ShieldCheck aria-hidden="true" className="h-[18px] w-[18px]" strokeWidth={1.5} />
          </span>
          <div>
            <p className="text-[17px] font-semibold leading-5 tracking-[-0.02em]">Pactra</p>
            <p className="mt-0.5 text-xs text-white/45">Payment control</p>
          </div>
        </div>

        <nav aria-label="Primary navigation" className="mt-9 space-y-1">
          {navigation.map(({ label, href, icon: Icon }, index) => (
            <a
              aria-current={index === 0 ? "page" : undefined}
              className={`flex h-9 items-center gap-3 rounded-lg px-3 text-sm transition-colors duration-150 ${
                index === 0
                  ? "bg-white/10 text-white"
                  : "text-white/55 hover:bg-white/[0.06] hover:text-white"
              }`}
              href={href}
              key={href}
            >
              <Icon aria-hidden="true" className="h-4 w-4" strokeWidth={1.5} />
              {label}
            </a>
          ))}
        </nav>

      </aside>

      <div className="min-w-0 lg:pl-60">
        <header className="sticky top-0 z-20 border-b border-line bg-canvas/95 backdrop-blur-md">
          <div className="flex h-16 items-center justify-between gap-4 px-4 sm:px-6 lg:px-8">
            <div className="flex items-center gap-3 lg:hidden">
              <span className="grid h-8 w-8 place-items-center rounded-lg bg-ink-950 text-white">
                <ShieldCheck aria-hidden="true" className="h-4 w-4" strokeWidth={1.5} />
              </span>
              <span className="text-base font-semibold tracking-[-0.02em]">Pactra</span>
            </div>
            <div className="hidden lg:block">
              <p className="text-sm font-medium text-ink-950">Overview</p>
            </div>
            <div className="flex items-center gap-2 text-xs text-ink-600">
              <span className="h-2 w-2 rounded-full bg-positive" />
              Policy online
            </div>
          </div>
          <nav
            aria-label="Mobile navigation"
            className="flex gap-1 overflow-x-auto border-t border-line px-3 py-2 lg:hidden"
          >
            {navigation.map(({ label, href }) => (
              <a
                className="shrink-0 rounded-lg px-3 py-2 text-xs font-medium text-ink-600 hover:bg-white hover:text-ink-950"
                href={href}
                key={href}
              >
                {label}
              </a>
            ))}
          </nav>
        </header>

        {error ? (
          <div className="fixed right-4 top-20 z-50 flex w-[calc(100%-2rem)] max-w-md items-start gap-3 rounded-xl border border-negative/20 bg-white p-4 text-sm text-ink-800 shadow-float sm:right-6">
            <Activity
              aria-hidden="true"
              className="mt-0.5 h-4 w-4 shrink-0 text-negative"
            />
            <span className="flex-1">{error}</span>
            <button
              aria-label="Dismiss error"
              className="rounded-md p-1 text-ink-500 hover:bg-canvas hover:text-ink-950"
              onClick={() => setError(null)}
              type="button"
            >
              <X aria-hidden="true" className="h-4 w-4" />
            </button>
          </div>
        ) : null}

        <main className="pactra-enter mx-auto max-w-[1560px] px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
          <div className="mb-6">
            <div>
              <h1 className="text-2xl font-medium tracking-[-0.02em] text-ink-950 sm:text-[28px]">
                Payment operations
              </h1>
              <p className="mt-1 text-sm text-ink-500">{today}</p>
            </div>
          </div>

          <PolicyOverview
            loading={loading}
            pendingCount={pendingCount}
            policy={policy}
            summaries={summaries}
          />

          <div className="mt-6 grid min-w-0 items-start gap-6 xl:grid-cols-[minmax(0,1.55fr)_minmax(340px,0.65fr)]">
            <TransactionLedger
              loading={loading}
              onError={setError}
              onRefresh={() => refreshData(true)}
              transactions={transactions}
            />
            <PaymentAgent onTransactionCreated={() => refreshData()} />
          </div>
        </main>
      </div>
    </div>
  );
}
