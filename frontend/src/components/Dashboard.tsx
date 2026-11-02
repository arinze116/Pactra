import { useMemo, useState } from "react";
import type { ColDef, ICellRendererParams, ValueFormatterParams } from "ag-grid-community";
import { AgGridReact } from "ag-grid-react";
import {
  ArrowUpRight,
  Check,
  Clock3,
  Filter,
  RefreshCw,
  ShieldCheck,
  X,
} from "lucide-react";
import { api } from "../api";
import type { Transaction, TransactionStatus } from "../types";
import { StatusBadge } from "./StatusBadge";

interface DashboardProps {
  transactions: Transaction[];
  loading: boolean;
  onRefresh: () => Promise<void> | void;
  onError: (message: string) => void;
}

type StatusFilter = "all" | TransactionStatus;

const filters: Array<{ value: StatusFilter; label: string }> = [
  { value: "all", label: "All" },
  { value: "approved", label: "Approved" },
  { value: "pending_approval", label: "Pending" },
  { value: "blocked", label: "Blocked" },
];

const money = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  minimumFractionDigits: 2,
});

const dateTime = new Intl.DateTimeFormat("en-NG", {
  month: "short",
  day: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});

function shortId(value: string | null) {
  if (!value) return "—";
  return value.length > 18 ? `${value.slice(0, 9)}…${value.slice(-5)}` : value;
}

export function Dashboard({
  transactions,
  loading,
  onRefresh,
  onError,
}: DashboardProps) {
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [approvalTarget, setApprovalTarget] = useState<Transaction | null>(null);
  const [approving, setApproving] = useState(false);

  const displayedTransactions = useMemo(
    () =>
      statusFilter === "all"
        ? transactions
        : transactions.filter((transaction) => transaction.status === statusFilter),
    [statusFilter, transactions],
  );

  async function approve() {
    if (!approvalTarget || approving) return;
    setApproving(true);
    try {
      await api.approveTransaction(approvalTarget.id);
      setApprovalTarget(null);
      await onRefresh();
    } catch (error) {
      onError(error instanceof Error ? error.message : "Approval failed");
    } finally {
      setApproving(false);
    }
  }

  const columnDefs = useMemo<ColDef<Transaction>[]>(
    () => [
      {
        headerName: "Vendor",
        field: "vendor",
        minWidth: 170,
        flex: 1.3,
        cellRenderer: ({ data }: ICellRendererParams<Transaction>) =>
          data ? (
            <div className="flex h-full items-center gap-3">
              <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-white/[0.045] text-[11px] font-bold uppercase text-slate-400 ring-1 ring-inset ring-white/[0.06]">
                {data.vendor.slice(0, 2)}
              </span>
              <div className="min-w-0 leading-tight">
                <p className="truncate text-xs font-semibold text-slate-200">{data.vendor}</p>
                <p className="mt-1 truncate text-[10px] capitalize text-slate-600">
                  {data.transaction_type} · {data.category}
                </p>
              </div>
            </div>
          ) : null,
      },
      {
        headerName: "Amount",
        field: "amount",
        width: 112,
        valueFormatter: ({ value }: ValueFormatterParams<Transaction, number>) =>
          money.format(value ?? 0),
        cellClass: "font-semibold text-slate-200",
      },
      {
        headerName: "Status",
        field: "status",
        width: 145,
        cellRenderer: ({ value }: ICellRendererParams<Transaction, TransactionStatus>) =>
          value ? <StatusBadge status={value} /> : null,
      },
      {
        headerName: "PayPal reference",
        field: "paypal_order_id",
        minWidth: 145,
        flex: 1,
        cellRenderer: ({ data }: ICellRendererParams<Transaction>) => (
          <div className="flex h-full items-center gap-1.5 font-mono text-[10px] text-slate-500">
            <span>{shortId(data?.paypal_order_id ?? null)}</span>
            {data?.paypal_order_id ? (
              <ArrowUpRight className="h-3 w-3 text-slate-700" aria-hidden="true" />
            ) : null}
          </div>
        ),
      },
      {
        headerName: "Time",
        field: "timestamp",
        width: 120,
        valueFormatter: ({ value }: ValueFormatterParams<Transaction, string>) =>
          value ? dateTime.format(new Date(value)) : "—",
        cellClass: "text-slate-500 text-[11px]",
      },
      {
        headerName: "",
        field: "id",
        width: 92,
        sortable: false,
        filter: false,
        cellRenderer: ({ data }: ICellRendererParams<Transaction>) =>
          data?.status === "pending_approval" ? (
            <button
              className="rounded-lg border border-amber-300/20 bg-amber-300/10 px-2.5 py-1.5 text-[10px] font-semibold text-amber-200 transition hover:bg-amber-300/15"
              onClick={() => setApprovalTarget(data)}
              type="button"
            >
              Review
            </button>
          ) : null,
      },
    ],
    [],
  );

  const defaultColDef = useMemo<ColDef<Transaction>>(
    () => ({
      sortable: true,
      filter: false,
      resizable: true,
      suppressMovable: true,
    }),
    [],
  );

  const pendingCount = transactions.filter(
    (transaction) => transaction.status === "pending_approval",
  ).length;

  return (
    <section className="flex min-h-[620px] min-w-0 flex-col overflow-hidden rounded-2xl border border-white/[0.07] bg-ink-850/70 shadow-panel lg:h-[calc(100vh-286px)] lg:min-h-[620px]">
      <header className="border-b border-white/[0.06] px-5 py-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="grid h-9 w-9 place-items-center rounded-xl bg-violet-400/10 text-violet-300 ring-1 ring-inset ring-violet-300/15">
              <ShieldCheck className="h-4.5 w-4.5" aria-hidden="true" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-sm font-semibold text-white">Transaction control room</h2>
                {pendingCount > 0 ? (
                  <span className="rounded-full bg-amber-300/10 px-1.5 py-0.5 text-[9px] font-bold text-amber-200">
                    {pendingCount} pending
                  </span>
                ) : null}
              </div>
              <p className="text-[11px] text-slate-500">Live policy decisions and PayPal outcomes</p>
            </div>
          </div>
          <button
            aria-label="Refresh dashboard"
            className="grid h-8 w-8 place-items-center rounded-lg border border-white/[0.06] bg-white/[0.025] text-slate-500 transition hover:text-white disabled:opacity-50"
            disabled={loading}
            onClick={() => void onRefresh()}
            type="button"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} aria-hidden="true" />
          </button>
        </div>

        <div className="mt-4 flex items-center gap-2 overflow-x-auto">
          <Filter className="mr-1 h-3.5 w-3.5 shrink-0 text-slate-600" aria-hidden="true" />
          {filters.map((filter) => (
            <button
              className={`shrink-0 rounded-lg px-2.5 py-1.5 text-[10px] font-semibold transition ${
                statusFilter === filter.value
                  ? "bg-white/[0.08] text-white"
                  : "text-slate-500 hover:bg-white/[0.03] hover:text-slate-300"
              }`}
              key={filter.value}
              onClick={() => setStatusFilter(filter.value)}
              type="button"
            >
              {filter.label}
            </button>
          ))}
          <span className="ml-auto shrink-0 text-[10px] text-slate-700">
            {displayedTransactions.length} records
          </span>
        </div>
      </header>

      <div className="ag-theme-quartz-dark relative min-h-0 flex-1">
        <AgGridReact<Transaction>
          animateRows
          columnDefs={columnDefs}
          defaultColDef={defaultColDef}
          getRowId={({ data }) => data.id}
          overlayNoRowsTemplate="<span class='pactra-empty'>No transactions match this view yet.</span>"
          pagination
          paginationPageSize={10}
          rowData={displayedTransactions}
          rowHeight={64}
          suppressCellFocus
          suppressPaginationPanel={displayedTransactions.length <= 10}
        />
        {loading ? (
          <div className="absolute inset-0 z-10 grid place-items-center bg-ink-850/60 backdrop-blur-[2px]">
            <div className="flex items-center gap-2 rounded-xl border border-white/[0.07] bg-ink-900 px-4 py-2.5 text-[11px] font-medium text-slate-400 shadow-xl">
              <RefreshCw className="h-3.5 w-3.5 animate-spin text-pactra-400" aria-hidden="true" />
              Refreshing control room
            </div>
          </div>
        ) : null}
      </div>

      {approvalTarget ? (
        <div
          aria-modal="true"
          className="fixed inset-0 z-50 grid place-items-center bg-black/70 p-4 backdrop-blur-sm"
          role="dialog"
        >
          <div className="w-full max-w-md rounded-2xl border border-white/[0.1] bg-ink-850 p-5 shadow-2xl">
            <div className="flex items-start justify-between gap-4">
              <div className="grid h-10 w-10 place-items-center rounded-xl bg-amber-300/10 text-amber-200">
                <Clock3 className="h-5 w-5" aria-hidden="true" />
              </div>
              <button
                aria-label="Close approval dialog"
                className="grid h-8 w-8 place-items-center rounded-lg text-slate-500 transition hover:bg-white/[0.04] hover:text-white"
                disabled={approving}
                onClick={() => setApprovalTarget(null)}
                type="button"
              >
                <X className="h-4 w-4" aria-hidden="true" />
              </button>
            </div>
            <h3 className="mt-4 text-lg font-semibold text-white">Approve this payment?</h3>
            <p className="mt-1 text-sm leading-6 text-slate-400">
              Pactra paused this request because it is above your automatic approval threshold.
            </p>
            <dl className="mt-5 space-y-3 rounded-xl border border-white/[0.06] bg-black/10 p-4 text-xs">
              <div className="flex justify-between gap-4">
                <dt className="text-slate-500">Vendor</dt>
                <dd className="font-medium text-slate-200">{approvalTarget.vendor}</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-slate-500">Amount</dt>
                <dd className="font-semibold text-white">{money.format(approvalTarget.amount)}</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-slate-500">Category</dt>
                <dd className="capitalize text-slate-300">{approvalTarget.category}</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-slate-500">Reason</dt>
                <dd className="max-w-[240px] text-right text-slate-300">{approvalTarget.reason}</dd>
              </div>
            </dl>
            <div className="mt-5 flex gap-3">
              <button
                className="flex-1 rounded-xl border border-white/[0.08] px-4 py-2.5 text-xs font-semibold text-slate-400 transition hover:bg-white/[0.04] hover:text-white"
                disabled={approving}
                onClick={() => setApprovalTarget(null)}
                type="button"
              >
                Cancel
              </button>
              <button
                className="flex flex-1 items-center justify-center gap-2 rounded-xl bg-pactra-400 px-4 py-2.5 text-xs font-bold text-ink-950 transition hover:bg-pactra-300 disabled:opacity-60"
                disabled={approving}
                onClick={() => void approve()}
                type="button"
              >
                {approving ? (
                  <RefreshCw className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
                ) : (
                  <Check className="h-3.5 w-3.5" aria-hidden="true" />
                )}
                Confirm approval
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </section>
  );
}
