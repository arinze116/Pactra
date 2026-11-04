/* eslint-disable react-refresh/only-export-components */
import type { LucideIcon } from "lucide-react";
import { AlertCircle, Inbox } from "lucide-react";
import type { TransactionStatus } from "../types";

export const money = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

export function formatCents(cents: number) { return money.format(cents / 100); }

const statusConfig: Record<TransactionStatus, { label: string; className: string; dot: string }> = {
  draft: { label: "Draft", className: "text-ink-600", dot: "bg-ink-400" },
  pending_approval: { label: "Needs approval", className: "text-warning-dark", dot: "bg-warning" },
  executing: { label: "Processing", className: "text-sky-800", dot: "bg-sky-500" },
  completed: { label: "Completed", className: "text-positive-dark", dot: "bg-positive" },
  blocked: { label: "Blocked", className: "text-negative", dot: "bg-negative" },
  rejected: { label: "Rejected", className: "text-negative", dot: "bg-negative" },
  failed: { label: "Failed", className: "text-negative", dot: "bg-negative" },
  cancelled: { label: "Cancelled", className: "text-ink-500", dot: "bg-ink-400" },
  reversed: { label: "Reversed", className: "text-indigo-700", dot: "bg-indigo-500" },
};

export function Status({ value }: { value: TransactionStatus }) {
  const item = statusConfig[value];
  return <span className={`inline-flex items-center gap-2 whitespace-nowrap text-xs font-medium ${item.className}`}><span className={`h-2 w-2 rounded-full ${item.dot}`} />{item.label}</span>;
}

export function PageHeader({ title, description, action }: { title: string; description?: string; action?: React.ReactNode }) {
  return <header className="mb-7 flex flex-wrap items-start justify-between gap-4"><div className="border-l-2 border-pactra-600 pl-4"><h1 className="text-[30px] font-medium leading-9 tracking-[-0.035em] text-ink-950 sm:text-[36px]">{title}</h1>{description ? <p className="mt-2 max-w-2xl text-sm leading-6 text-ink-500">{description}</p> : null}</div>{action}</header>;
}

export function Panel({ children, className = "" }: { children?: React.ReactNode; className?: string }) {
  return <section className={`rounded-[14px] border border-line bg-surface shadow-card ${className}`}>{children}</section>;
}

export function EmptyState({ title, description, icon: Icon = Inbox }: { title: string; description: string; icon?: LucideIcon }) {
  return <div className="grid min-h-56 place-items-center px-6 py-10 text-center"><div><Icon className="mx-auto h-5 w-5 text-ink-400" strokeWidth={1.5} /><p className="mt-3 text-sm font-medium text-ink-800">{title}</p><p className="mt-1 text-sm text-ink-500">{description}</p></div></div>;
}

export function ErrorNotice({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return <div className="flex items-start gap-3 rounded-xl border border-negative/20 bg-negative-soft px-4 py-3 text-sm text-negative"><AlertCircle className="mt-0.5 h-4 w-4 shrink-0" /><span className="flex-1">{message}</span>{onRetry ? <button className="shrink-0 font-medium underline decoration-negative/30 underline-offset-4" onClick={onRetry} type="button">Try again</button> : null}</div>;
}

export function LoadingBlock({ className = "h-24" }: { className?: string }) {
  return <div aria-busy="true" aria-label="Loading" className={`loading-placeholder rounded-xl border border-line bg-surface ${className}`} />;
}
