import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AgGridReact } from "ag-grid-react";
import type { CellKeyDownEvent, ColDef, RowClickedEvent } from "ag-grid-community";
import "ag-grid-community/styles/ag-grid.css";
import "ag-grid-community/styles/ag-theme-quartz.css";
import { ArrowLeft, Check, ClipboardCopy, RefreshCw, X } from "lucide-react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { api, createIdempotencyKey, isAmbiguousMutationError } from "../api";
import { EmptyState, ErrorNotice, formatCents, LoadingBlock, PageHeader, Panel, Status } from "../components/UI";
import type { Transaction, TransactionDetail, TransactionStatus, TransactionType } from "../types";

export function ApprovalsPage() {
  const [items, setItems] = useState<Transaction[]>([]);
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

  async function act(item: Transaction, action: "approve" | "reject") {
    const keys = action === "approve" ? approvalKeysRef.current : rejectionKeysRef.current;
    const requestKey = keys.get(item.id) ?? createIdempotencyKey(action);
    keys.set(item.id, requestKey);
    setBusy(item.id);
    setError("");
    try {
      if (action === "approve") await api.approve(item.id, requestKey);
      else await api.reject(item.id, reason.trim(), requestKey);
      keys.delete(item.id);
      setRejecting(null);
      setReason("");
      await load();
    } catch (caught) {
      if (!isAmbiguousMutationError(caught)) keys.delete(item.id);
      setError(caught instanceof Error ? caught.message : "Approval action failed");
    } finally {
      setBusy(null);
    }
  }

  return <>
    <PageHeader title="Approvals" description="Oldest requests appear first. Every approval rechecks the current policy and wallet." />
    {error ? <div className="mb-5"><ErrorNotice message={error} onRetry={() => void load()} /></div> : null}
    <Panel>
      {loading ? <div className="space-y-3 p-5"><LoadingBlock className="h-28" /><LoadingBlock className="h-28" /></div> : items.length ? <div className="divide-y divide-line">{items.map((item) => <article className="grid gap-5 p-5 sm:p-6 lg:grid-cols-[1fr_auto] lg:items-center" key={item.id}><div><div className="flex flex-wrap items-center gap-3"><h2 className="text-base font-medium">{item.vendor}</h2><Status value={item.status} /></div><p className="mt-2 text-sm text-ink-600">{item.reason}</p><dl className="mt-4 flex flex-wrap gap-x-8 gap-y-2 text-xs"><div><dt className="text-ink-400">Amount</dt><dd className="mt-1 font-medium tabular-nums text-ink-800">{formatCents(item.amount_cents)}</dd></div><div><dt className="text-ink-400">Category</dt><dd className="mt-1 capitalize text-ink-800">{item.category}</dd></div><div><dt className="text-ink-400">Rail</dt><dd className="mt-1 text-ink-800">{item.rail === "internal_sandbox" ? "Internal sandbox" : "PayPal Sandbox"}</dd></div></dl>{rejecting === item.id ? <label className="mt-5 block max-w-xl text-xs font-medium text-ink-600">Rejection reason for {item.vendor}<textarea className="input mt-2 min-h-20 resize-y py-2" maxLength={300} onChange={(event) => { rejectionKeysRef.current.delete(item.id); setReason(event.target.value); }} placeholder="Optional context for the audit trail" value={reason} /></label> : null}</div><div className="flex flex-wrap gap-2">{rejecting === item.id ? <><button className="action-secondary" disabled={busy === item.id} onClick={() => { rejectionKeysRef.current.delete(item.id); setRejecting(null); setReason(""); }} type="button">Cancel</button><button className="inline-flex h-10 items-center gap-2 rounded-lg border border-negative/30 px-4 text-sm font-medium text-negative disabled:opacity-50" disabled={busy === item.id} onClick={() => void act(item, "reject")} type="button"><X className="h-4 w-4" />Confirm rejection</button></> : <><button className="action-secondary" disabled={busy === item.id} onClick={() => { if (rejecting) rejectionKeysRef.current.delete(rejecting); rejectionKeysRef.current.delete(item.id); setRejecting(item.id); setReason(""); }} type="button"><X className="h-4 w-4" />Reject</button><button className="action-primary" disabled={busy === item.id} onClick={() => void act(item, "approve")} type="button"><Check className="h-4 w-4" />Approve</button></>}</div></article>)}</div> : <EmptyState title="No requests need approval" description="Requests above your approval threshold will appear here" />}
    </Panel>
  </>;
}

const statuses: Array<"all" | TransactionStatus> = ["all", "draft", "pending_approval", "executing", "completed", "blocked", "rejected", "failed", "cancelled", "reversed"];
const transactionTypes: Array<"all" | TransactionType> = ["all", "vendor_payment", "payout", "sandbox_transfer"];

export function TransactionsPage() {
  const navigate = useNavigate();
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

  const columns = useMemo<ColDef<Transaction>[]>(() => [
    { field: "vendor", headerName: "Vendor", flex: 1.4, minWidth: 180 },
    { field: "amount_cents", headerName: "Amount", width: 130, valueFormatter: ({ value }) => formatCents(Number(value)), cellClass: "tabular-nums" },
    { field: "category", headerName: "Category", width: 125 },
    { field: "status", headerName: "Status", width: 150, cellRenderer: ({ value }: { value: TransactionStatus }) => <Status value={value} /> },
    { field: "rail", headerName: "Rail", minWidth: 160, valueFormatter: ({ value }) => value === "internal_sandbox" ? "Internal sandbox" : "PayPal Sandbox" },
    { field: "created_at", headerName: "Created", width: 170, valueFormatter: ({ value }) => new Intl.DateTimeFormat("en-NG", { dateStyle: "medium", timeStyle: "short" }).format(new Date(String(value))) },
  ], []);

  function open(event: RowClickedEvent<Transaction>) {
    if (event.data) navigate(`/app/transactions/${event.data.id}`);
  }

  function openWithKeyboard(event: CellKeyDownEvent<Transaction>) {
    if ((event.event as KeyboardEvent | undefined)?.key === "Enter" && event.data) navigate(`/app/transactions/${event.data.id}`);
  }

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
      {loading ? <div className="p-5"><LoadingBlock className="h-[520px]" /></div> : items.length ? <><div className="ag-theme-quartz hidden h-[590px] md:block"><AgGridReact<Transaction> columnDefs={columns} rowData={items} onCellKeyDown={openWithKeyboard} onRowClicked={open} pagination paginationPageSize={25} rowSelection="single" /></div><div className="divide-y divide-line md:hidden">{items.map((item) => <Link className="block p-5" key={item.id} to={`/app/transactions/${item.id}`}><div className="flex justify-between gap-4"><div><p className="text-sm font-medium">{item.vendor}</p><p className="mt-1 text-xs text-ink-500">{item.category} · {item.rail === "internal_sandbox" ? "Internal" : "PayPal"}</p></div><p className="text-sm font-medium tabular-nums">{formatCents(item.amount_cents)}</p></div><div className="mt-4"><Status value={item.status} /></div></Link>)}</div>{nextCursor ? <div className="border-t border-line p-4 text-center"><button className="action-secondary" disabled={loadingMore} onClick={loadMore} type="button">{loadingMore ? "Loading more" : "Load more transactions"}</button></div> : null}</> : <EmptyState title="No matching transactions" description="Adjust the filters or create a payment request" />}
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

  async function copyId() {
    await navigator.clipboard.writeText(transaction.id);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1500);
  }

  return <>
    <Link className="mb-5 inline-flex items-center gap-2 text-sm text-ink-500 hover:text-ink-950" to="/app/transactions"><ArrowLeft className="h-4 w-4" />Transactions</Link>
    <PageHeader title="Transaction receipt" description={`Pactra ID ${transaction.id}`} action={<div className="flex flex-wrap gap-2"><button className="action-secondary" onClick={() => void copyId()} type="button"><ClipboardCopy className="h-4 w-4" />{copied ? "Copied" : "Copy ID"}</button>{transaction.status === "failed" ? <button className="action-secondary" disabled={busy} onClick={() => void action("retry")}>Retry</button> : null}{transaction.status === "completed" && transaction.rail === "internal_sandbox" ? <button className="action-secondary" disabled={busy} onClick={() => void action("reverse")}>Reverse</button> : null}{transaction.rail === "paypal_sandbox_payouts" && transaction.status === "executing" ? <button className="action-secondary" disabled={busy} onClick={() => void action("reconcile")}><RefreshCw className="h-4 w-4" />Refresh provider</button> : null}</div>} />
    {error ? <div className="mb-5"><ErrorNotice message={error} onRetry={() => void load()} /></div> : null}
    <div className="grid gap-6 xl:grid-cols-[1fr_0.72fr]">
      <div className="space-y-6">
        <Panel className="p-5 sm:p-6"><div className="flex flex-wrap items-start justify-between gap-4"><div><Status value={transaction.status} />{transaction.rail === "paypal_sandbox_payouts" && transaction.status === "executing" ? <p className="mt-2 text-xs font-medium text-sky-800">Provider pending. Reserved funds remain held until the payout item reaches a terminal state.</p> : null}<h2 className="mt-4 text-2xl font-medium">{transaction.vendor}</h2><p className="mt-2 text-sm text-ink-500">{transaction.reason}</p></div><p className="text-3xl font-medium tabular-nums">{formatCents(transaction.amount_cents)}</p></div><dl className="mt-7 grid gap-5 border-t border-line pt-6 text-sm sm:grid-cols-2"><Info label="Category" value={transaction.category} /><Info label="Rail" value={transaction.rail === "internal_sandbox" ? "Internal sandbox" : "PayPal Sandbox Payouts"} /><Info label="Policy version" value={`v${transaction.policy_version}`} /><Info label="Sandbox generation" value={String(transaction.sandbox_generation)} /><Info label="Provider status" value={transaction.provider_status ?? "Not applicable"} /><Info label="Provider reference" value={transaction.provider_item_id ?? transaction.provider_batch_id ?? transaction.rail_reference ?? "Not available"} />{transaction.failure_code ? <Info label="Failure code" value={transaction.failure_code} /> : null}</dl></Panel>
        <Panel><div className="border-b border-line px-5 py-4 sm:px-6"><h2 className="text-sm font-medium">Policy trace</h2></div><ol className="policy-trace space-y-5 p-5 text-sm sm:p-6">{detail.policy_checks.map((check, index) => <li className="flex gap-3" key={index}><span>{index + 1}</span><div><p className="font-medium text-ink-800">{String(check.code ?? "Policy check").replace(/_/g, " ")}</p><p className={`mt-1 text-xs ${check.passed ? "text-positive-dark" : "text-negative"}`}>{check.passed ? "Passed" : String(check.message ?? "Stopped here")}</p></div></li>)}</ol></Panel>
        {detail.attempts.length ? <Panel><div className="border-b border-line px-5 py-4 sm:px-6"><h2 className="text-sm font-medium">Execution attempts</h2></div><div className="divide-y divide-line">{detail.attempts.map((attempt, index) => <div className="grid gap-2 p-5 text-sm sm:grid-cols-3" key={String(attempt.id ?? index)}><div><p className="text-xs text-ink-400">Attempt</p><p className="mt-1 font-medium">#{String(attempt.attempt_number ?? index + 1)}</p></div><div><p className="text-xs text-ink-400">Status</p><p className="mt-1 font-medium capitalize">{String(attempt.status ?? "unknown").replace(/_/g, " ")}</p></div><div><p className="text-xs text-ink-400">Provider</p><p className="mt-1 break-all font-mono text-xs">{String(attempt.provider_status ?? attempt.response_code ?? "Internal sandbox")}</p></div></div>)}</div></Panel> : null}
      </div>
      <div className="space-y-6">
        <Panel><div className="border-b border-line px-5 py-4"><h2 className="text-sm font-medium">Lifecycle</h2></div><div className="divide-y divide-line">{detail.events.map((event, index) => <div className="p-4" key={String(event.id ?? index)}><p className="text-sm font-medium">{String(event.event_type ?? "Event").replace(/_/g, " ")}</p><p className="mt-1 text-xs text-ink-500">{event.created_at ? new Date(String(event.created_at)).toLocaleString() : ""}</p></div>)}</div></Panel>
        <Panel><div className="border-b border-line px-5 py-4"><h2 className="text-sm font-medium">Ledger impact</h2></div>{detail.ledger_entries.length ? <div className="divide-y divide-line">{detail.ledger_entries.map((entry, index) => <div className="flex justify-between gap-4 p-4 text-sm" key={String(entry.entry_id ?? index)}><div><p className="font-medium capitalize">{String(entry.direction)}</p><p className="mt-1 text-xs text-ink-500">{String(entry.journal_type).replace(/_/g, " ")}</p></div><p className="font-mono tabular-nums">{formatCents(Number(entry.amount_cents))}</p></div>)}</div> : <EmptyState title="No posted ledger entries" description="Pending and blocked requests do not move posted funds" />}</Panel>
      </div>
    </div>
  </>;
}

function Info({ label, value }: { label: string; value: string }) {
  return <div><dt className="text-xs text-ink-400">{label}</dt><dd className="mt-1 break-all font-medium capitalize text-ink-800">{value}</dd></div>;
}
