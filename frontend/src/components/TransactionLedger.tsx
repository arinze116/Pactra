import { useEffect, useMemo, useRef, useState } from "react";
import {
  Check,
  ChevronLeft,
  ChevronRight,
  Clock3,
  RefreshCw,
  ShieldCheck,
  X,
} from "lucide-react";
import { api } from "../api";
import type { Transaction, TransactionStatus } from "../types";
import { DecisionStatus } from "./DecisionStatus";

interface TransactionLedgerProps {
  transactions: Transaction[];
  loading: boolean;
  onRefresh: () => Promise<void> | void;
  onError: (message: string) => void;
}

type StatusFilter = "all" | TransactionStatus;

const filters: Array<{ value: StatusFilter; label: string; shortLabel: string }> = [
  { value: "all", label: "All decisions", shortLabel: "All" },
  { value: "approved", label: "Approved", shortLabel: "Approved" },
  { value: "pending_approval", label: "Needs approval", shortLabel: "Approval" },
  { value: "blocked", label: "Blocked", shortLabel: "Blocked" },
];

const PAGE_SIZE = 8;

const money = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const dateTime = new Intl.DateTimeFormat("en-NG", {
  month: "short",
  day: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});

function shortId(value: string | null) {
  if (!value) return "No PayPal reference";
  return value.length > 24 ? `${value.slice(0, 12)}…${value.slice(-6)}` : value;
}

export function TransactionLedger({
  transactions,
  loading,
  onRefresh,
  onError,
}: TransactionLedgerProps) {
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [approvalTarget, setApprovalTarget] = useState<Transaction | null>(null);
  const [approving, setApproving] = useState(false);
  const [page, setPage] = useState(0);
  const closeButtonRef = useRef<HTMLButtonElement>(null);

  const filteredTransactions = useMemo(
    () =>
      statusFilter === "all"
        ? transactions
        : transactions.filter((transaction) => transaction.status === statusFilter),
    [statusFilter, transactions],
  );

  const pageCount = Math.max(Math.ceil(filteredTransactions.length / PAGE_SIZE), 1);
  const displayedTransactions = filteredTransactions.slice(
    page * PAGE_SIZE,
    page * PAGE_SIZE + PAGE_SIZE,
  );

  useEffect(() => {
    setPage(0);
  }, [statusFilter]);

  useEffect(() => {
    if (page >= pageCount) setPage(pageCount - 1);
  }, [page, pageCount]);

  useEffect(() => {
    if (!approvalTarget) return;
    closeButtonRef.current?.focus();
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !approving) setApprovalTarget(null);
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [approvalTarget, approving]);

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

  return (
    <section
      aria-labelledby="transactions-title"
      className="relative min-w-0 overflow-hidden rounded-2xl border border-line bg-white shadow-card"
      id="transactions"
    >
      <header className="border-b border-line px-5 py-5 sm:px-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="flex items-center gap-3">
            <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-canvas text-ink-700">
              <ShieldCheck aria-hidden="true" className="h-5 w-5" strokeWidth={1.5} />
            </span>
            <div>
              <h2 className="text-sm font-medium text-ink-950" id="transactions-title">
                Transaction ledger
              </h2>
              <p className="mt-1 text-xs text-ink-500">
                Policy decisions and PayPal outcomes
              </p>
            </div>
          </div>
          <button
            aria-label="Refresh transactions"
            className="grid h-9 w-9 place-items-center rounded-lg border border-line text-ink-500 transition-colors duration-150 hover:bg-canvas hover:text-ink-950 disabled:opacity-50"
            disabled={loading}
            onClick={() => void onRefresh()}
            type="button"
          >
            <RefreshCw
              aria-hidden="true"
              className={`h-4 w-4 ${loading ? "animate-spin" : ""}`}
              strokeWidth={1.5}
            />
          </button>
        </div>

        <div className="mt-5 flex items-center gap-1 overflow-x-auto rounded-lg bg-canvas p-1">
          {filters.map((filter) => (
            <button
              aria-pressed={statusFilter === filter.value}
              className={`shrink-0 rounded-md px-3 py-2 text-xs font-medium transition-colors duration-150 ${
                statusFilter === filter.value
                  ? "bg-white text-ink-950 shadow-sm"
                  : "text-ink-500 hover:text-ink-950"
              }`}
              key={filter.value}
              onClick={() => setStatusFilter(filter.value)}
              type="button"
            >
              <span className="sm:hidden">{filter.shortLabel}</span>
              <span className="hidden sm:inline">{filter.label}</span>
            </button>
          ))}
          <span className="ml-auto hidden shrink-0 px-2 font-mono text-xs text-ink-400 sm:block">
            {filteredTransactions.length} records
          </span>
        </div>
      </header>

      {displayedTransactions.length > 0 ? (
        <>
          <div className="hidden overflow-x-auto md:block">
            <table className="w-full min-w-[620px] border-collapse text-left">
              <thead>
                <tr className="border-b border-line text-xs text-ink-500">
                  <th className="px-6 py-3 font-normal">Vendor</th>
                  <th className="px-4 py-3 font-normal">Amount</th>
                  <th className="px-4 py-3 font-normal">Decision</th>
                  <th className="px-4 py-3 font-normal">Time</th>
                  <th className="px-4 py-3 text-right font-normal">
                    <span className="sr-only">Action</span>
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {displayedTransactions.map((transaction) => (
                  <tr className="transition-colors duration-150 hover:bg-canvas/60" key={transaction.id}>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg border border-line bg-canvas font-mono text-xs text-ink-600">
                          {transaction.vendor.slice(0, 2).toUpperCase()}
                        </span>
                        <div className="min-w-0">
                          <p className="truncate text-sm font-medium text-ink-950">
                            {transaction.vendor}
                          </p>
                          <p className="mt-1 truncate font-mono text-[11px] text-ink-400">
                            {transaction.category} · {shortId(transaction.paypal_order_id)}
                          </p>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-4 font-mono text-sm tabular-nums text-ink-950">
                      {money.format(transaction.amount)}
                    </td>
                    <td className="px-4 py-4">
                      <DecisionStatus status={transaction.status} />
                    </td>
                    <td className="px-4 py-4">
                      <time
                        className="whitespace-nowrap text-xs text-ink-500"
                        dateTime={transaction.timestamp}
                      >
                        {dateTime.format(new Date(transaction.timestamp))}
                      </time>
                    </td>
                    <td className="px-4 py-4 text-right">
                      {transaction.status === "pending_approval" ? (
                        <button
                          className="rounded-lg border border-warning/30 bg-warning-soft px-3 py-2 text-xs font-medium text-warning-dark transition-colors duration-150 hover:bg-warning/15"
                          onClick={() => setApprovalTarget(transaction)}
                          type="button"
                        >
                          Review
                        </button>
                      ) : (
                        <span className="text-xs text-ink-300">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="divide-y divide-line md:hidden">
            {displayedTransactions.map((transaction) => (
              <article className="p-5" key={transaction.id}>
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-medium text-ink-950">{transaction.vendor}</p>
                    <p className="mt-1 font-mono text-xs text-ink-400">
                      {shortId(transaction.paypal_order_id)}
                    </p>
                  </div>
                  <p className="font-mono text-sm font-medium tabular-nums text-ink-950">
                    {money.format(transaction.amount)}
                  </p>
                </div>
                <div className="mt-4 flex items-center justify-between gap-3">
                  <DecisionStatus status={transaction.status} />
                  <time className="text-xs text-ink-500" dateTime={transaction.timestamp}>
                    {dateTime.format(new Date(transaction.timestamp))}
                  </time>
                </div>
                {transaction.status === "pending_approval" ? (
                  <button
                    className="mt-4 w-full rounded-lg border border-warning/30 bg-warning-soft px-3 py-2 text-xs font-medium text-warning-dark"
                    onClick={() => setApprovalTarget(transaction)}
                    type="button"
                  >
                    Review payment
                  </button>
                ) : null}
              </article>
            ))}
          </div>
        </>
      ) : (
        <div className="grid min-h-64 place-items-center px-6 py-12 text-center">
          <div>
            <p className="text-sm font-medium text-ink-800">No decisions in this view</p>
            <p className="mt-2 text-sm text-ink-500">
              New governed payments will appear here
            </p>
          </div>
        </div>
      )}

      <footer className="flex items-center justify-between gap-4 border-t border-line px-5 py-4 sm:px-6">
        <p className="font-mono text-xs text-ink-400">
          Page {page + 1} of {pageCount}
        </p>
        <div className="flex gap-2">
          <button
            aria-label="Previous page"
            className="grid h-8 w-8 place-items-center rounded-lg border border-line text-ink-500 hover:bg-canvas disabled:cursor-not-allowed disabled:opacity-35"
            disabled={page === 0}
            onClick={() => setPage((current) => Math.max(current - 1, 0))}
            type="button"
          >
            <ChevronLeft aria-hidden="true" className="h-4 w-4" />
          </button>
          <button
            aria-label="Next page"
            className="grid h-8 w-8 place-items-center rounded-lg border border-line text-ink-500 hover:bg-canvas disabled:cursor-not-allowed disabled:opacity-35"
            disabled={page >= pageCount - 1}
            onClick={() => setPage((current) => Math.min(current + 1, pageCount - 1))}
            type="button"
          >
            <ChevronRight aria-hidden="true" className="h-4 w-4" />
          </button>
        </div>
      </footer>

      {loading ? (
        <div className="absolute inset-0 z-10 grid place-items-center bg-white/80 backdrop-blur-[2px]">
          <div className="flex items-center gap-2 rounded-lg border border-line bg-white px-4 py-3 text-xs text-ink-600 shadow-card">
            <RefreshCw aria-hidden="true" className="h-4 w-4 animate-spin text-pactra-700" />
            Refreshing ledger
          </div>
        </div>
      ) : null}

      {approvalTarget ? (
        <div
          aria-labelledby="approval-title"
          aria-modal="true"
          className="fixed inset-0 z-50 grid place-items-center bg-ink-950/70 p-4"
          role="dialog"
        >
          <div className="w-full max-w-md rounded-2xl bg-white p-5 shadow-float sm:p-6">
            <div className="flex items-start justify-between gap-4">
              <span className="grid h-10 w-10 place-items-center rounded-xl bg-warning-soft text-warning-dark">
                <Clock3 aria-hidden="true" className="h-5 w-5" strokeWidth={1.5} />
              </span>
              <button
                aria-label="Close approval dialog"
                className="grid h-8 w-8 place-items-center rounded-lg text-ink-500 hover:bg-canvas hover:text-ink-950"
                disabled={approving}
                onClick={() => setApprovalTarget(null)}
                ref={closeButtonRef}
                type="button"
              >
                <X aria-hidden="true" className="h-4 w-4" />
              </button>
            </div>
            <h3 className="mt-5 text-xl font-medium tracking-[-0.02em] text-ink-950" id="approval-title">
              Review payment exception
            </h3>
            <p className="mt-2 text-sm leading-6 text-ink-600">
              This request exceeded the automatic approval threshold. Confirm the details before releasing it to PayPal.
            </p>
            <dl className="mt-6 divide-y divide-line rounded-xl border border-line px-4 text-sm">
              <div className="flex justify-between gap-4 py-3">
                <dt className="text-ink-500">Vendor</dt>
                <dd className="font-medium text-ink-950">{approvalTarget.vendor}</dd>
              </div>
              <div className="flex justify-between gap-4 py-3">
                <dt className="text-ink-500">Amount</dt>
                <dd className="font-mono font-medium tabular-nums text-ink-950">
                  {money.format(approvalTarget.amount)}
                </dd>
              </div>
              <div className="flex justify-between gap-4 py-3">
                <dt className="text-ink-500">Category</dt>
                <dd className="capitalize text-ink-800">{approvalTarget.category}</dd>
              </div>
              <div className="flex justify-between gap-4 py-3">
                <dt className="text-ink-500">Reason</dt>
                <dd className="max-w-[240px] text-right text-ink-800">{approvalTarget.reason}</dd>
              </div>
            </dl>
            <div className="mt-6 flex gap-3">
              <button
                className="flex-1 rounded-lg border border-line px-4 py-2.5 text-sm font-medium text-ink-600 hover:bg-canvas hover:text-ink-950"
                disabled={approving}
                onClick={() => setApprovalTarget(null)}
                type="button"
              >
                Cancel
              </button>
              <button
                className="flex flex-1 items-center justify-center gap-2 rounded-lg bg-ink-950 px-4 py-2.5 text-sm font-medium text-white hover:bg-ink-800 disabled:opacity-60"
                disabled={approving}
                onClick={() => void approve()}
                type="button"
              >
                {approving ? (
                  <RefreshCw aria-hidden="true" className="h-4 w-4 animate-spin" />
                ) : (
                  <Check aria-hidden="true" className="h-4 w-4" />
                )}
                Approve payment
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </section>
  );
}
