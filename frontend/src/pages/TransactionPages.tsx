import { lazy, Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ArrowLeft, Check, ClipboardCopy, RefreshCw, X } from "lucide-react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { api, createIdempotencyKey, isAmbiguousMutationError } from "../api";
import { EmptyState, ErrorNotice, formatCents, LoadingBlock, PageHeader, Panel, Status } from "../components/UI";
import type { ApprovalItem, Transaction, TransactionDetail, TransactionStatus, TransactionType } from "../types";

const TransactionGrid = lazy(() => import("../components/TransactionGrid"));

export function ApprovalsPage() {
  const [items, setItems] = useState<ApprovalItem[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [rejecting, setRejecting] = useState<string | null>(null);
  const [reason, setReason] = useState("");
  const approvalKeysRef = useRef(new Map<string, string>());
  const rejectionKeysRef = useRef(new Map<string, string>());

  const load = useCallback(() => {
    setError("");
    setLoading(true);
    return api.approvals()
      .then((result) => setItems(result.items))
      .catch((caught) => setError(caught instanceof Error ? caught.message : "Approvals unavailable"))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { void load(); }, [load]);

  async function act(item: ApprovalItem, action: "approve" | "reject") {
    const transaction = item.transaction;
    const keys = action === "approve" ? approvalKeysRef.current : rejectionKeysRef.current;
    const requestKey = keys.get(transaction.id) ?? createIdempotencyKey(action);
    keys.set(transaction.id, requestKey);
    setBusy(transaction.id);
    setError("");
    try {
      if (action === "approve") await api.approve(transaction.id, requestKey);
      else await api.reject(transaction.id, reason.trim(), requestKey);
      keys.delete(transaction.id);
      setRejecting(null);
      setReason("");
      await load();
    } catch (caught) {
      if (!isAmbiguousMutationError(caught)) keys.delete(transaction.id);
      setError(caught instanceof Error ? caught.message : "Approval action failed");
    } finally {
      setBusy(null);
    }
  }

  return <>
    <PageHeader title="Approvals" description="Oldest requests appear first. Every approval rechecks the current policy and wallet." />
    {error ? <div className="mb-5"><ErrorNotice message={error} onRetry={() => void load()} /></div> : null}
    <Panel>
      {loading ? <div className="space-y-3 p-5"><LoadingBlock className="h-28" /><LoadingBlock className="h-28" /></div> : items.length ? <div className="divide-y divide-line">{items.map((item) => { const transaction = item.transaction; return <article className="grid gap-5 p-5 sm:p-6 lg:grid-cols-[1fr_auto] lg:items-center" key={transaction.id}><div><div className="flex flex-wrap items-center gap-3"><h2 className="text-base font-medium">{transaction.vendor}</h2><Status value={transaction.status} /></div><p className="mt-2 text-sm text-ink-600">{transaction.reason}</p><dl className="mt-4 grid gap-x-8 gap-y-3 text-xs sm:grid-cols-2 xl:grid-cols-4"><ApprovalFact label="Requester" value={item.requester.email} /><ApprovalFact label="Amount" value={formatCents(transaction.amount_cents)} /><ApprovalFact label="Category" value={transaction.category} /><ApprovalFact label="Available balance" value={formatCents(item.available_balance.available_cents)} /><ApprovalFact label="Created" value={new Date(transaction.created_at).toLocaleString()} /><ApprovalFact label="Age" value={formatAge(transaction.created_at)} /><ApprovalFact label="Rail" value={transaction.rail === "internal_sandbox" ? "Internal sandbox" : "PayPal Sandbox"} /><ApprovalFact label="Current policy" value={`v${item.current_policy_version} · ${item.current_policy_decision.replace(/_/g, " ")}`} /></dl><div className="mt-4 rounded-xl bg-canvas p-4"><p className="text-xs font-medium text-ink-700">Policy checks</p><ul className="mt-2 grid gap-1 text-xs text-ink-500 sm:grid-cols-2">{item.policy_checks.map((check, index) => <li key={`${String(check.code)}-${index}`}>{check.passed ? "Pass" : "Stop"}: {String(check.code ?? "policy check").replace(/_/g, " ")}</li>)}</ul>{item.current_policy_reason_code ? <p className="mt-2 text-xs font-medium text-negative">{item.current_policy_reason_code.replace(/_/g, " ")}</p> : null}</div>{rejecting === transaction.id ? <label className="mt-5 block max-w-xl text-xs font-medium text-ink-600">Rejection reason for {transaction.vendor}<textarea className="input mt-2 min-h-20 resize-y py-2" maxLength={300} onChange={(event) => { rejectionKeysRef.current.delete(transaction.id); setReason(event.target.value); }} placeholder="Optional context for the audit trail" value={reason} /></label> : null}</div><div className="flex flex-wrap gap-2">{rejecting === transaction.id ? <><button className="action-secondary" disabled={busy === transaction.id} onClick={() => { rejectionKeysRef.current.delete(transaction.id); setRejecting(null); setReason(""); }} type="button">Cancel</button><button className="inline-flex h-10 items-center gap-2 rounded-lg border border-negative/30 px-4 text-sm font-medium text-negative disabled:opacity-50" disabled={busy === transaction.id} onClick={() => void act(item, "reject")} type="button"><X className="h-4 w-4" />Confirm rejection</button></> : <><button className="action-secondary" disabled={busy === transaction.id} onClick={() => { if (rejecting) rejectionKeysRef.current.delete(rejecting); rejectionKeysRef.current.delete(transaction.id); setRejecting(transaction.id); setReason(""); }} type="button"><X className="h-4 w-4" />Reject</button><button className="action-primary" disabled={busy === transaction.id} onClick={() => void act(item, "approve")} type="button"><Check className="h-4 w-4" />Approve</button></>}</div></article>; })}</div> : <EmptyState title="No requests need approval" description="Requests above your approval threshold will appear here" />}
    </Panel>
  </>;
}

function ApprovalFact({ label, value }: { label: string; value: string }) {
  return <div><dt className="text-ink-400">{label}</dt><dd className="mt-1 break-words font-medium text-ink-800">{value}</dd></div>;
}

function formatAge(createdAt: string) {
  const seconds = Math.max(0, Math.floor((Date.now() - new Date(createdAt).getTime()) / 1000));
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m`;
  const hours = Math.floor(minutes / 60);
  return hours < 24 ? `${hours}h` : `${Math.floor(hours / 24)}d`;
}

const statuses: Array<"all" | TransactionStatus> = ["all", "draft", "pending_approval", "executing", "completed", "blocked", "rejected", "failed", "cancelled", "reversed"];
const transactionTypes: Array<"all" | TransactionType> = ["all", "vendor_payment", "payout", "sandbox_transfer"];

export function TransactionsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [items, setItems] = useState<Transaction[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const requestSequenceRef = useRef(0);
  const statusParam = searchParams.get("status") ?? "all";
  const status = statuses.includes(statusParam as "all" | TransactionStatus) ? statusParam as "all" | TransactionStatus : "all";
  const vendor = searchParams.get("vendor") ?? "";
  const category = searchParams.get("category") ?? "all";
  const typeParam = searchParams.get("type") ?? "all";
  const transactionType = transactionTypes.includes(typeParam as "all" | TransactionType) ? typeParam as "all" | TransactionType : "all";
  const generation = searchParams.get("generation") === "all" ? "all" : "current";
  const from = searchParams.get("from") ?? "";
  const to = searchParams.get("to") ?? "";

  const updateFilter = (name: string, value: string, defaultValue = "") => {
    const next = new URLSearchParams(searchParams);
    if (!value || value === defaultValue) next.delete(name);
    else next.set(name, value);
    setSearchParams(next, { replace: true });
  };

  const buildQuery = useCallback((cursor?: string) => {
    const params = new URLSearchParams({ limit: "100", generation });
    if (status !== "all") params.set("status", status);
    if (vendor.trim()) params.set("vendor", vendor.trim());
    if (category !== "all") params.set("category", category);
    if (transactionType !== "all") params.set("type", transactionType);
    if (from) params.set("from", from);
    if (to) params.set("to", to);
    if (cursor) params.set("cursor", cursor);
    return params.toString();
  }, [category, from, generation, status, to, transactionType, vendor]);

  const runLoad = useCallback(async (cursor: string | null, append: boolean, sequence: number) => {
    if (append) setLoadingMore(true);
    else {
      setLoading(true);
      setItems([]);
      setNextCursor(null);
    }
    setError("");
    try {
      const result = await api.transactions(buildQuery(cursor ?? undefined));
      if (sequence !== requestSequenceRef.current) return;
      setItems((current) => {
        if (!append) return result.items;
        const existing = new Set(current.map((item) => item.id));
        return [...current, ...result.items.filter((item) => !existing.has(item.id))];
      });
      setNextCursor(result.next_cursor);
    } catch (caught) {
      if (sequence === requestSequenceRef.current) {
        setError(caught instanceof Error ? caught.message : "Transactions unavailable");
      }
    } finally {
      if (sequence === requestSequenceRef.current) {
        if (append) setLoadingMore(false);
        else setLoading(false);
      }
    }
  }, [buildQuery]);

  useEffect(() => {
    const sequence = ++requestSequenceRef.current;
    setLoading(true);
    setLoadingMore(false);
    setItems([]);
    setNextCursor(null);
    setError("");
    const timer = window.setTimeout(() => { void runLoad(null, false, sequence); }, 180);
    return () => {
      window.clearTimeout(timer);
      requestSequenceRef.current += 1;
    };
  }, [runLoad]);

  useEffect(() => {
    let active = true;
    api.policy()
      .then((result) => { if (active) setCategories(result.policy.allowed_categories); })
      .catch(() => undefined);
    return () => { active = false; };
  }, []);

  function retryLoad() {
    const sequence = ++requestSequenceRef.current;
    void runLoad(null, false, sequence);
  }

  function loadMore() {
    if (!nextCursor || loadingMore) return;
    const sequence = ++requestSequenceRef.current;
    void runLoad(nextCursor, true, sequence);
  }

  const filterCategories = useMemo(() => [...new Set([
    ...categories,
    ...items.map((item) => item.category),
    ...(category === "all" ? [] : [category]),
  ])].sort(), [categories, category, items]);
  const hasFilters = status !== "all" || vendor || category !== "all" || transactionType !== "all" || generation !== "current" || from || to;

  return <>
    <PageHeader title="Transactions" description="Filter the operational ledger, then open any row for its policy and execution receipt" />
    {error ? <div className="mb-5"><ErrorNotice message={error} onRetry={retryLoad} /></div> : null}
    <Panel className="overflow-hidden">
      <div className="grid gap-3 border-b border-line p-4 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-8">
        <label className="text-xs text-ink-500">Status<select className="mt-1 h-10 w-full rounded-lg border border-line bg-surface-raised px-3 text-sm text-ink-800" onChange={(event) => updateFilter("status", event.target.value, "all")} value={status}>{statuses.map((item) => <option key={item} value={item}>{item === "all" ? "All statuses" : item.replace(/_/g, " ")}</option>)}</select></label>
        <label className="text-xs text-ink-500">Type<select className="mt-1 h-10 w-full rounded-lg border border-line bg-surface-raised px-3 text-sm text-ink-800" onChange={(event) => updateFilter("type", event.target.value, "all")} value={transactionType}>{transactionTypes.map((item) => <option key={item} value={item}>{item === "all" ? "All types" : item.replace(/_/g, " ")}</option>)}</select></label>
        <label className="text-xs text-ink-500">Category<select className="mt-1 h-10 w-full rounded-lg border border-line bg-surface-raised px-3 text-sm text-ink-800" onChange={(event) => updateFilter("category", event.target.value, "all")} value={category}><option value="all">All categories</option>{filterCategories.map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
        <label className="text-xs text-ink-500 xl:col-span-2">Vendor<input className="mt-1 h-10 w-full rounded-lg border border-line bg-surface-raised px-3 text-sm text-ink-800" onChange={(event) => updateFilter("vendor", event.target.value)} placeholder="Search vendor" value={vendor} /></label>
        <label className="text-xs text-ink-500">From<input className="mt-1 h-10 w-full rounded-lg border border-line bg-surface-raised px-3 text-sm text-ink-800" max={to || undefined} onChange={(event) => updateFilter("from", event.target.value)} type="date" value={from} /></label>
        <label className="text-xs text-ink-500">To<input className="mt-1 h-10 w-full rounded-lg border border-line bg-surface-raised px-3 text-sm text-ink-800" min={from || undefined} onChange={(event) => updateFilter("to", event.target.value)} type="date" value={to} /></label>
        <label className="text-xs text-ink-500">History<select className="mt-1 h-10 w-full rounded-lg border border-line bg-surface-raised px-3 text-sm text-ink-800" onChange={(event) => updateFilter("generation", event.target.value, "current")} value={generation}><option value="current">Current sandbox</option><option value="all">All history</option></select></label>
        <div className="flex items-center justify-between gap-3 border-t border-line pt-3 sm:col-span-2 lg:col-span-4 xl:col-span-8"><span className="text-xs tabular-nums text-ink-400">{items.length} loaded records</span>{hasFilters ? <button className="text-xs font-medium text-ink-700 underline decoration-line underline-offset-4" onClick={() => setSearchParams({}, { replace: true })} type="button">Clear filters</button> : null}</div>
      </div>
      {loading ? <div className="p-5"><LoadingBlock className="h-[520px]" /></div> : items.length ? <><Suspense fallback={<div className="hidden p-5 md:block"><LoadingBlock className="h-[520px]" /></div>}><TransactionGrid items={items} /></Suspense><div className="divide-y divide-line md:hidden">{items.map((item) => <Link className="block p-5" key={item.id} to={`/app/transactions/${item.id}`}><div className="flex justify-between gap-4"><div><p className="text-sm font-medium">{item.vendor}</p><p className="mt-1 text-xs text-ink-500">{item.category} · {item.rail === "internal_sandbox" ? "Internal" : "PayPal"}</p></div><p className="text-sm font-medium tabular-nums">{formatCents(item.amount_cents)}</p></div><div className="mt-4"><Status value={item.status} /></div></Link>)}</div>{nextCursor ? <div className="border-t border-line p-4 text-center"><button className="action-secondary" disabled={loadingMore} onClick={loadMore} type="button">{loadingMore ? "Loading more" : "Load more transactions"}</button></div> : null}</> : <EmptyState title="No matching transactions" description="Adjust the filters or create a payment request" />}
    </Panel>
  </>;
}

export function ReceiptPage() {
  const { id = "" } = useParams();
  const [detail, setDetail] = useState<TransactionDetail | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);
  const actionKeysRef = useRef(new Map<"retry" | "reverse", string>());

  const load = useCallback(() => {
    setError("");
    return api.transaction(id)
      .then(setDetail)
      .catch((caught) => setError(caught instanceof Error ? caught.message : "Receipt unavailable"));
  }, [id]);

  useEffect(() => { void load(); }, [load]);

  async function action(kind: "retry" | "reverse" | "reconcile") {
    if (!detail) return;
    if (kind === "reverse" && !window.confirm("Create a compensating sandbox reversal? The original ledger entries remain immutable.")) return;
    const latestAttempt = detail.attempts.at(-1);
    const isAmbiguousSubmissionRecovery = kind === "reconcile"
      && detail.transaction.provider_batch_id == null
      && latestAttempt?.status === "unknown";
    if (isAmbiguousSubmissionRecovery && !window.confirm(
      "Recover this ambiguous Sandbox submission? Pactra will reuse the original stable PayPal request identifiers. It will not create a new payout attempt.",
    )) return;
    const requestKey = kind === "reconcile" ? null : actionKeysRef.current.get(kind) ?? createIdempotencyKey(kind);
    if (kind !== "reconcile" && requestKey) actionKeysRef.current.set(kind, requestKey);
    setBusy(true);
    setError("");
    try {
      if (kind === "retry" && requestKey) await api.retry(id, requestKey);
      if (kind === "reverse" && requestKey) await api.reverse(id, "Operator-requested sandbox reversal", requestKey);
      if (kind === "reconcile") await api.reconcile(id);
      if (kind !== "reconcile") actionKeysRef.current.delete(kind);
      await load();
    } catch (caught) {
      if (kind !== "reconcile" && !isAmbiguousMutationError(caught)) actionKeysRef.current.delete(kind);
      setError(caught instanceof Error ? caught.message : "Action failed");
    } finally {
      setBusy(false);
    }
  }

  if (!detail) return <><PageHeader title="Transaction receipt" />{error ? <ErrorNotice message={error} onRetry={() => void load()} /> : <LoadingBlock className="h-72" />}</>;
  const transaction = detail.transaction;
  const latestAttempt = detail.attempts.at(-1);
  const isAmbiguousSubmissionRecovery = transaction.rail === "paypal_sandbox_payouts"
    && transaction.status === "executing"
    && transaction.provider_batch_id == null
    && latestAttempt?.status === "unknown";
  const debitTotal = detail.ledger_entries.reduce((total, entry) => entry.direction === "debit" ? total + Number(entry.amount_cents) : total, 0);
  const creditTotal = detail.ledger_entries.reduce((total, entry) => entry.direction === "credit" ? total + Number(entry.amount_cents) : total, 0);

  async function copyId() {
    await navigator.clipboard.writeText(transaction.id);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1500);
  }

  return <>
    <Link className="mb-5 inline-flex items-center gap-2 text-sm text-ink-500 hover:text-ink-950" to="/app/transactions"><ArrowLeft className="h-4 w-4" />Transactions</Link>
    <PageHeader title="Transaction receipt" description={`Pactra ID ${transaction.id}`} action={<div className="flex flex-wrap gap-2"><button className="action-secondary" onClick={() => void copyId()} type="button"><ClipboardCopy className="h-4 w-4" />{copied ? "Copied" : "Copy ID"}</button>{transaction.status === "failed" ? <button className="action-secondary" disabled={busy} onClick={() => void action("retry")}>Retry</button> : null}{transaction.status === "completed" && transaction.rail === "internal_sandbox" ? <button className="action-secondary" disabled={busy} onClick={() => void action("reverse")}>Reverse</button> : null}{transaction.rail === "paypal_sandbox_payouts" && transaction.status === "executing" ? <button className="action-secondary" disabled={busy} onClick={() => void action("reconcile")}><RefreshCw className="h-4 w-4" />{isAmbiguousSubmissionRecovery ? "Recover submission" : "Refresh provider"}</button> : null}</div>} />
    {error ? <div className="mb-5"><ErrorNotice message={error} onRetry={() => void load()} /></div> : null}
    <div className="grid gap-6 xl:grid-cols-[1fr_0.72fr]">
      <div className="space-y-6">
        <Panel className="p-5 sm:p-6"><div className="flex flex-wrap items-start justify-between gap-4"><div><Status value={transaction.status} />{transaction.rail === "paypal_sandbox_payouts" && transaction.status === "executing" ? <p className="mt-2 max-w-2xl text-xs font-medium text-sky-800">{isAmbiguousSubmissionRecovery ? "Provider outcome unknown. Reserved funds remain held. Recovery reuses the original stable provider request and does not create a new attempt." : "Provider pending. Reserved funds remain held until the payout item reaches a terminal state."}</p> : null}<h2 className="mt-4 text-2xl font-medium">{transaction.vendor}</h2><p className="mt-2 text-sm text-ink-500">{transaction.reason}</p></div><p className="text-3xl font-medium tabular-nums">{formatCents(transaction.amount_cents)}</p></div><dl className="mt-7 grid gap-5 border-t border-line pt-6 text-sm sm:grid-cols-2">{transaction.recipient ? <Info label="Recipient" value={transaction.recipient} /> : null}<Info label="Category" value={transaction.category} /><Info label="Rail" value={transaction.rail === "internal_sandbox" ? "Internal sandbox" : "PayPal Sandbox Payouts"} /><Info label="Policy version" value={`v${transaction.policy_version}`} /><Info label="Sandbox generation" value={String(transaction.sandbox_generation)} /><Info label={transaction.rail === "internal_sandbox" ? "Provider evidence" : "Provider status"} value={transaction.rail === "internal_sandbox" ? "Not applicable — internal ledger only" : transaction.provider_status ?? "Awaiting provider status"} /><Info label={transaction.rail === "internal_sandbox" ? "Internal execution reference" : "Provider reference"} value={transaction.provider_item_id ?? transaction.provider_batch_id ?? transaction.rail_reference ?? "Not available"} />{transaction.failure_code ? <Info label="Failure code" value={transaction.failure_code} /> : null}</dl></Panel>
        <Panel><div className="border-b border-line px-5 py-4 sm:px-6"><h2 className="text-sm font-medium">Policy trace</h2></div><ol className="policy-trace space-y-5 p-5 text-sm sm:p-6">{detail.policy_checks.map((check, index) => <li className="flex gap-3" key={index}><span>{index + 1}</span><div><p className="font-medium text-ink-800">{String(check.code ?? "Policy check").replace(/_/g, " ")}</p><p className={`mt-1 text-xs ${check.passed ? "text-positive-dark" : "text-negative"}`}>{check.passed ? "Passed" : String(check.message ?? "Stopped here")}</p></div></li>)}</ol></Panel>
        {detail.attempts.length ? <Panel><div className="border-b border-line px-5 py-4 sm:px-6"><h2 className="text-sm font-medium">Execution attempts</h2></div><div className="divide-y divide-line">{detail.attempts.map((attempt, index) => { const evidence = executionEvidence(attempt); return <div className="grid gap-2 p-5 text-sm sm:grid-cols-3" key={String(attempt.id ?? index)}><div><p className="text-xs text-ink-400">Attempt</p><p className="mt-1 font-medium">#{String(attempt.attempt_number ?? index + 1)}</p></div><div><p className="text-xs text-ink-400">Status</p><p className="mt-1 font-medium capitalize">{String(attempt.status ?? "unknown").replace(/_/g, " ")}</p></div><div><p className="text-xs text-ink-400">{evidence.label}</p><p className="mt-1 break-all font-mono text-xs">{evidence.value}</p></div></div>; })}</div></Panel> : null}
      </div>
      <div className="space-y-6">
        <Panel><div className="border-b border-line px-5 py-4"><h2 className="text-sm font-medium">Lifecycle</h2></div><div className="divide-y divide-line">{detail.events.map((event, index) => <div className="p-4" key={String(event.id ?? index)}><div className="flex items-start justify-between gap-3"><p className="text-sm font-medium">{String(event.event_type ?? "Event").replace(/_/g, " ")}</p><span className="text-xs font-medium text-ink-400">{String(event.actor_label ?? "Pactra system")}</span></div><p className="mt-2 text-xs leading-5 text-ink-600">{String(event.summary ?? "Lifecycle event recorded")}</p><p className="mt-1 text-xs text-ink-400">{event.created_at ? new Date(String(event.created_at)).toLocaleString() : ""}</p></div>)}</div></Panel>
        <Panel><div className="border-b border-line px-5 py-4"><h2 className="text-sm font-medium">Ledger impact</h2>{detail.ledger_entries.length ? <p className={`mt-1 text-xs ${debitTotal === creditTotal ? "text-positive-dark" : "text-negative"}`}>{formatCents(debitTotal)} debits = {formatCents(creditTotal)} credits</p> : null}</div>{detail.ledger_entries.length ? <div className="divide-y divide-line">{detail.ledger_entries.map((entry, index) => <div className="flex justify-between gap-4 p-4 text-sm" key={String(entry.entry_id ?? index)}><div><p className="font-medium capitalize">{String(entry.direction)} · {String(entry.account_label ?? "Ledger account")}</p><p className="mt-1 text-xs text-ink-500">Counter-account: {String(entry.counter_account_label ?? "Balanced counter-account")}</p><p className="mt-1 text-xs text-ink-400">{String(entry.journal_type).replace(/_/g, " ")} · {entry.created_at ? new Date(String(entry.created_at)).toLocaleString() : ""}</p></div><p className="font-mono tabular-nums">{formatCents(Number(entry.amount_cents))} {String(entry.currency ?? "USD")}</p></div>)}</div> : <EmptyState title="No posted ledger entries" description="No ledger posting has occurred. Pending and blocked requests do not move posted funds." />}</Panel>
      </div>
    </div>
  </>;
}

function Info({ label, value }: { label: string; value: string }) {
  return <div><dt className="text-xs text-ink-400">{label}</dt><dd className="mt-1 break-words font-medium text-ink-800">{value}</dd></div>;
}

function executionEvidence(attempt: Record<string, unknown>) {
  if (attempt.rail === "internal_sandbox") {
    return { label: "Evidence", value: "Internal ledger capture" };
  }
  return {
    label: "Provider item",
    value: String(attempt.provider_status ?? attempt.response_code ?? "Awaiting provider status"),
  };
}
