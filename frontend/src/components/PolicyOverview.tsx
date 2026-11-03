import { ArrowDownRight, Check, Clock3, ShieldCheck } from "lucide-react";
import type { Policy, SpendSummary } from "../types";

interface PolicyOverviewProps {
  policy: Policy | null;
  summaries: SpendSummary[];
  loading: boolean;
  pendingCount: number;
}

const money = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});

const policyChecks = [
  "Category",
  "Vendor",
  "Transaction limit",
  "Daily limit",
  "Category budget",
  "Approval",
];

export function PolicyOverview({
  policy,
  summaries,
  loading,
  pendingCount,
}: PolicyOverviewProps) {
  const totalSpent = summaries.reduce((sum, item) => sum + item.spent_today, 0);
  const dailyLimit = policy?.daily_limit ?? 0;
  const dailyRemaining = Math.max(dailyLimit - totalSpent, 0);
  const dailyUtilisation = dailyLimit
    ? Math.min((totalSpent / dailyLimit) * 100, 100)
    : 0;

  return (
    <section aria-labelledby="policy-overview-title" id="overview">
      <span className="sr-only" id="policy">
        Active policy
      </span>
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1.55fr)_minmax(280px,0.45fr)]">
        <article className="rounded-2xl border border-line bg-white p-5 shadow-card sm:p-6">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <div className="flex items-center gap-2 text-sm font-medium text-ink-800">
                <ShieldCheck
                  aria-hidden="true"
                  className="h-4 w-4 text-pactra-700"
                  strokeWidth={1.5}
                />
                <h2 id="policy-overview-title">Daily policy runway</h2>
              </div>
              <p className="mt-2 text-sm text-ink-500">
                Spend approved today against the active workspace limit
              </p>
            </div>
            <div className="flex items-center gap-2 font-mono text-xs text-ink-500">
              <span className="h-2 w-2 rounded-full bg-positive" />
              Live policy
            </div>
          </div>

          <div className="mt-8 flex flex-wrap items-end justify-between gap-4">
            <div>
              <p className="font-mono text-xs text-ink-500">Spent today</p>
              <p className="mt-2 text-4xl font-medium tracking-[-0.035em] text-ink-950 sm:text-5xl">
                {money.format(totalSpent)}
                <span className="ml-2 text-base font-normal tracking-normal text-ink-500">
                  of {money.format(dailyLimit)}
                </span>
              </p>
            </div>
            <div className="text-left sm:text-right">
              <p className="font-mono text-xs text-ink-500">Available today</p>
              <p className="mt-1 text-xl font-medium tabular-nums text-ink-950">
                {money.format(dailyRemaining)}
              </p>
            </div>
          </div>

          <div className="mt-6 h-2 overflow-hidden rounded-full bg-canvas-deep">
            <div
              aria-hidden="true"
              className="h-full rounded-full bg-pactra-700 transition-[width] duration-500 ease-out"
              style={{ width: `${dailyUtilisation}%` }}
            />
          </div>
          <div className="mt-2 flex justify-between font-mono text-xs text-ink-500">
            <span>{dailyUtilisation.toFixed(0)}% used</span>
            <span>{money.format(dailyLimit)} limit</span>
          </div>

          <div className="mt-8 border-t border-line pt-5">
            <p className="font-mono text-xs text-ink-500">Policy path</p>
            <ol className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3 xl:grid-cols-6">
              {policyChecks.map((check, index) => (
                <li
                  className="relative flex min-h-12 items-center gap-2 rounded-lg border border-line bg-canvas px-3 text-xs text-ink-700"
                  key={check}
                >
                  <span className="grid h-5 w-5 shrink-0 place-items-center rounded-md bg-white font-mono text-[10px] text-pactra-700 shadow-sm">
                    {index + 1}
                  </span>
                  <span>{check}</span>
                </li>
              ))}
            </ol>
          </div>
        </article>

        <aside className="rounded-2xl border border-line bg-ink-950 p-5 text-white shadow-card sm:p-6">
          <p className="text-sm font-medium">Policy thresholds</p>
          <p className="mt-1 text-xs leading-5 text-white/45">
            The limits currently governing agent actions
          </p>
          <dl className="mt-6 divide-y divide-white/10">
            <div className="flex items-center justify-between gap-4 py-4 first:pt-0">
              <dt className="flex items-center gap-2 text-sm text-white/55">
                <Check aria-hidden="true" className="h-4 w-4" strokeWidth={1.5} />
                Automatic approval
              </dt>
              <dd className="font-mono text-sm tabular-nums">
                ≤ {money.format(policy?.require_approval_above ?? 0)}
              </dd>
            </div>
            <div className="flex items-center justify-between gap-4 py-4">
              <dt className="flex items-center gap-2 text-sm text-white/55">
                <ArrowDownRight
                  aria-hidden="true"
                  className="h-4 w-4"
                  strokeWidth={1.5}
                />
                Per payment cap
              </dt>
              <dd className="font-mono text-sm tabular-nums">
                {money.format(policy?.per_transaction_limit ?? 0)}
              </dd>
            </div>
            <div className="flex items-center justify-between gap-4 py-4 last:pb-0">
              <dt className="flex items-center gap-2 text-sm text-white/55">
                <Clock3 aria-hidden="true" className="h-4 w-4" strokeWidth={1.5} />
                Pending review
              </dt>
              <dd className="font-mono text-sm tabular-nums">
                {pendingCount} {pendingCount === 1 ? "request" : "requests"}
              </dd>
            </div>
          </dl>
        </aside>
      </div>

      <article className="mt-4 rounded-2xl border border-line bg-white p-5 shadow-card sm:p-6">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h2 className="text-sm font-medium text-ink-950">Category budgets</h2>
            <p className="mt-1 text-sm text-ink-500">
              Remaining capacity by approved payment category
            </p>
          </div>
          <span className="font-mono text-xs text-ink-500">
            {policy?.approved_categories.length ?? 0} approved categories
          </span>
        </div>

        <div className="mt-5 grid grid-cols-2 gap-x-6 gap-y-6 xl:grid-cols-4">
          {loading && summaries.length === 0
            ? Array.from({ length: 4 }, (_, index) => (
                <div className="h-20 animate-pulse rounded-xl bg-canvas" key={index} />
              ))
            : summaries.map((item) => (
                <div key={item.category}>
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-sm font-medium capitalize text-ink-800">
                      {item.category}
                    </span>
                    <span className="font-mono text-xs text-ink-500">
                      {item.utilisation_pct.toFixed(0)}%
                    </span>
                  </div>
                  <p className="mt-2 text-xl font-medium tabular-nums text-ink-950">
                    {money.format(item.remaining)}
                    <span className="ml-1 text-xs font-normal text-ink-500">left</span>
                  </p>
                  <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-canvas-deep">
                    <div
                      className="h-full rounded-full bg-pactra-600"
                      style={{ width: `${Math.min(item.utilisation_pct, 100)}%` }}
                    />
                  </div>
                </div>
              ))}
        </div>
      </article>
    </section>
  );
}
