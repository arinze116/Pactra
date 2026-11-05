import { useCallback, useEffect, useMemo, useState } from "react";
import { ArrowRight, Check, Circle, Plus, ShieldCheck } from "lucide-react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { EmptyState, ErrorNotice, formatCents, LoadingBlock, PageHeader, Panel, Status } from "../components/UI";
import type { PayPalStatus, SpendSummary, Transaction, WalletBalance } from "../types";

export function OverviewPage() {
  const [wallet, setWallet] = useState<WalletBalance | null>(null);
  const [summary, setSummary] = useState<SpendSummary | null>(null);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [approvals, setApprovals] = useState(0);
  const [paypal, setPaypal] = useState<PayPalStatus | null>(null);
  const [error, setError] = useState("");
  const [paypalError, setPaypalError] = useState("");
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setError("");
    setPaypalError("");
    setLoading(true);
    const [coreResult, paypalResult] = await Promise.allSettled([
      Promise.all([
      api.wallet(),
      api.spendSummary(),
      api.transactions("limit=100"),
      api.approvals(),
      ]),
      api.paypalStatus(),
    ]);

    if (coreResult.status === "fulfilled") {
      const [nextWallet, nextSummary, nextTransactions, nextApprovals] = coreResult.value;
      setWallet(nextWallet);
      setSummary(nextSummary);
      setTransactions(nextTransactions.items);
      setApprovals(nextApprovals.items.length);
    } else {
      setError(coreResult.reason instanceof Error ? coreResult.reason.message : "Overview unavailable");
    }

    if (paypalResult.status === "fulfilled") {
      setPaypal(paypalResult.value);
    } else {
      setPaypal(null);
      setPaypalError(paypalResult.reason instanceof Error ? paypalResult.reason.message : "PayPal Sandbox status unavailable");
    }
    setLoading(false);
  }, []);

  useEffect(() => { void load(); }, [load]);

  const dailyUsed = (summary?.daily_committed_cents ?? 0) + (summary?.daily_reserved_cents ?? 0);
  const dailyPct = summary?.daily_limit_cents ? Math.min(100, (dailyUsed / summary.daily_limit_cents) * 100) : 0;
  const recentTransactions = transactions.slice(0, 6);

  const guidedSteps = useMemo(() => {
    const has = (predicate: (transaction: Transaction) => boolean) => transactions.some(predicate);
    const approvalPending = has((transaction) => transaction.vendor === "Ada Contractor" && transaction.status === "pending_approval");
    const rejectionPending = has((transaction) => transaction.vendor === "Contractor" && transaction.status === "pending_approval");
    return [
      { label: "Complete a $49 software payment", done: has((transaction) => transaction.vendor === "Linear" && transaction.amount_cents === 4_900 && transaction.status === "completed"), to: "/app/payments/new?scenario=auto", action: "Create" },
      { label: "Approve a $125 contractor payout", done: has((transaction) => transaction.vendor === "Ada Contractor" && transaction.amount_cents === 12_500 && transaction.status === "completed"), to: approvalPending ? "/app/approvals" : "/app/payments/new?scenario=approval", action: approvalPending ? "Review" : "Create" },
      { label: "Trigger the $185 policy block", done: has((transaction) => transaction.vendor === "AWS" && transaction.amount_cents === 18_500 && transaction.status === "blocked"), to: "/app/payments/new?scenario=blocked", action: "Test" },
      { label: "Reject a pending exception", done: has((transaction) => transaction.vendor === "Contractor" && transaction.status === "rejected"), to: rejectionPending ? "/app/approvals" : "/app/payments/new?scenario=reject", action: rejectionPending ? "Review" : "Create" },
      { label: "Reset and verify the clean baseline", done: (wallet?.sandbox_generation ?? 1) > 1, to: "/app/wallet", action: "Reset" },
    ];
  }, [transactions, wallet?.sandbox_generation]);
  const nextStep = guidedSteps.find((step) => !step.done);

  return <>
    <PageHeader title="Payment operations" description="Live sandbox position, policy capacity, and requests that need attention" action={<Link className="action-primary" to="/app/payments/new"><Plus className="h-4 w-4" />New payment</Link>} />
    {error ? <div className="mb-5"><ErrorNotice message={error} onRetry={() => void load()} /></div> : null}
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-12">
      {wallet ? <><Metric className="xl:col-span-4" label="Available" value={formatCents(wallet.available_cents)} /><Metric className="xl:col-span-3" label="Reserved" value={formatCents(wallet.reserved_cents)} /><Metric className="xl:col-span-3" label="Posted balance" value={formatCents(wallet.posted_cents)} /><Metric className="xl:col-span-2" label="Pending approvals" value={String(approvals)} /></> : loading ? Array.from({ length: 4 }, (_, index) => <LoadingBlock key={index} className={`h-28 ${index === 0 ? "xl:col-span-4" : index === 3 ? "xl:col-span-2" : "xl:col-span-3"}`} />) : null}
    </div>
    <div className="mt-6 grid gap-6 xl:grid-cols-[1.5fr_0.7fr]">
      <Panel>
        <div className="flex items-center justify-between border-b border-line px-5 py-4 sm:px-6"><div><h2 className="text-sm font-medium">Recent transactions</h2><p className="mt-1 text-xs text-ink-500">Current sandbox generation</p></div><Link className="text-xs font-medium text-ink-600" to="/app/transactions">View all</Link></div>
        {recentTransactions.length ? <div className="divide-y divide-line">{recentTransactions.map((item) => <Link className="grid gap-3 px-5 py-4 hover:bg-canvas/60 sm:grid-cols-[1fr_auto_auto] sm:items-center sm:px-6" key={item.id} to={`/app/transactions/${item.id}`}><div><p className="text-sm font-medium">{item.vendor}</p><p className="mt-1 text-xs text-ink-500">{item.category} · {item.rail === "internal_sandbox" ? "Internal sandbox" : "PayPal Sandbox"}</p></div><Status value={item.status} /><p className="text-sm font-medium tabular-nums sm:text-right">{formatCents(item.amount_cents)}</p></Link>)}</div> : <EmptyState title="No payment activity" description="Create the first governed sandbox request" />}
      </Panel>
      <Panel className="overflow-hidden">
        <div className="bg-canvas-deep p-5 sm:p-6"><div className="flex items-center gap-2 text-xs text-ink-500"><ShieldCheck className="h-4 w-4 text-pactra-300" />Daily policy capacity</div><p className="mt-3 text-3xl font-medium tabular-nums text-ink-950">{summary ? formatCents(Math.max(0, summary.daily_limit_cents - dailyUsed)) : "—"}</p><p className="mt-1 text-xs text-ink-500">remaining today</p><div className="mt-5 h-1.5 overflow-hidden rounded-full bg-surface-raised"><div className="h-full bg-pactra-600" style={{ width: `${dailyPct}%` }} /></div><p className="mt-2 text-xs text-ink-500">{dailyPct.toFixed(0)}% committed or reserved</p></div>
        <div className="p-5 sm:p-6"><div className="flex items-center justify-between gap-3"><h3 className="text-sm font-medium">Judge walkthrough</h3><span className="text-xs tabular-nums text-ink-400">{guidedSteps.filter((step) => step.done).length}/{guidedSteps.length}</span></div><ol className="mt-4 space-y-4 text-sm">{guidedSteps.map((step) => <li className="flex items-center gap-3" key={step.label}>{step.done ? <span className="grid h-5 w-5 place-items-center rounded-full bg-emerald-950 text-positive-dark"><Check className="h-3 w-3" /></span> : <Circle className="h-5 w-5 text-ink-300" />}<span className={`flex-1 ${step.done ? "text-ink-400 line-through" : "text-ink-700"}`}>{step.label}</span>{!step.done ? <Link className="text-xs font-medium text-pactra-300" to={step.to}>{step.action}</Link> : null}</li>)}</ol>{nextStep ? <Link className="action-primary mt-6 w-full" to={nextStep.to}>Continue guided test <ArrowRight className="h-4 w-4" /></Link> : <p className="mt-6 rounded-xl bg-emerald-950/50 p-4 text-sm text-positive-dark">Core internal sandbox scenarios are complete. Reset to run them again.</p>}</div>
      </Panel>
    </div>
    {summary ? <Panel className="mt-6"><div className="flex items-center justify-between border-b border-line px-5 py-4 sm:px-6"><h2 className="text-sm font-medium">Category capacity</h2><Link className="text-xs font-medium text-ink-600" to="/app/policies">Edit policy</Link></div><div className="grid gap-6 p-5 sm:grid-cols-2 sm:p-6 xl:grid-cols-4">{summary.categories.map((item) => <div key={item.category}><div className="flex justify-between text-xs"><span className="capitalize text-ink-600">{item.category}</span><span className="font-mono text-ink-400">{item.utilisation_percent.toFixed(0)}%</span></div><p className="mt-2 text-xl font-medium tabular-nums">{formatCents(item.remaining_cents)} <span className="text-xs font-normal text-ink-400">left</span></p><div className="mt-3 h-1.5 overflow-hidden rounded-full bg-canvas-deep"><div className="h-full bg-pactra-600" style={{ width: `${Math.min(100, item.utilisation_percent)}%` }} /></div></div>)}</div></Panel> : null}
    <Panel className="mt-6 flex flex-wrap items-center justify-between gap-4 p-5 sm:p-6"><div><p className="text-sm font-medium">PayPal Sandbox Payouts</p><p aria-live="polite" className="mt-1 text-xs text-ink-500">{paypalError ? `Status could not be verified (${paypalError}); internal sandbox remains fully available` : paypal?.configured ? "Configured for a real sandbox provider test" : "Not configured; internal sandbox remains fully available"}</p></div><Link className="action-secondary" to="/app/settings/integrations/paypal">View status</Link></Panel>
  </>;
}

function Metric({ className, label, value }: { className?: string; label: string; value: string }) {
  return <Panel className={`p-5 ${className ?? ""}`}><p className="text-xs text-ink-500">{label}</p><p className="mt-3 truncate text-2xl font-medium tabular-nums">{value}</p></Panel>;
}
