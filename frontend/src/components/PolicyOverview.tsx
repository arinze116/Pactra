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
  const isInitialLoading = loading && policy === null && summaries.length === 0;
  const policyAmount = (value: number | undefined) =>
    value === undefined ? "—" : money.format(value);

  const metrics = [
    { label: "Spent today", value: isInitialLoading ? "—" : money.format(totalSpent) },
    { label: "Available", value: isInitialLoading ? "—" : money.format(dailyRemaining) },
    {
      label: "Pending review",
      value: isInitialLoading ? "—" : pendingCount.toLocaleString("en-US"),
    },
    {
      label: "Auto-approve to",
      value: policyAmount(policy?.require_approval_above),
    },
  ];

  return (
    <section
      aria-labelledby="policy-overview-title"
      className="overflow-hidden rounded-2xl border border-line bg-white shadow-card"
      id="overview"
    >
      <div className="border-b border-line px-5 py-4 sm:px-6">
        <h2 className="text-sm font-medium text-ink-950" id="policy-overview-title">
          Today’s position
        </h2>
        <p className="mt-1 text-xs text-ink-500">Approved payment activity</p>
      </div>

      <dl className="grid grid-cols-2 divide-x divide-y divide-line sm:grid-cols-4 sm:divide-y-0">
        {metrics.map((metric) => (
          <div className="min-w-0 px-5 py-5 sm:px-6" key={metric.label}>
            <dt className="text-xs text-ink-500">{metric.label}</dt>
            <dd className="mt-2 truncate text-2xl font-medium tabular-nums tracking-[-0.02em] text-ink-950">
              {metric.value}
            </dd>
          </div>
        ))}
      </dl>

      <div className="border-t border-line px-5 py-4 sm:px-6">
        <div className="flex items-center justify-between gap-4 text-xs">
          <span className="text-ink-600">Daily limit used</span>
          <span className="font-mono tabular-nums text-ink-500">
            {isInitialLoading ? "—" : `${dailyUtilisation.toFixed(0)}% of ${money.format(dailyLimit)}`}
          </span>
        </div>
        <div
          aria-label={`${dailyUtilisation.toFixed(0)} percent of the daily payment limit used`}
          aria-valuemax={100}
          aria-valuemin={0}
          aria-valuenow={Math.round(dailyUtilisation)}
          className="mt-3 h-1.5 overflow-hidden rounded-full bg-canvas-deep"
          role="progressbar"
        >
          <div
            className="h-full rounded-full bg-pactra-700"
            style={{ width: `${dailyUtilisation}%` }}
          />
        </div>
      </div>

      <div className="grid border-t border-line lg:grid-cols-[minmax(0,1fr)_280px]">
        <div className="px-5 py-5 sm:px-6">
          <div className="flex items-center justify-between gap-4">
            <h3 className="text-sm font-medium text-ink-950">Category capacity</h3>
            <span className="font-mono text-xs text-ink-400">
              {policy?.approved_categories.length ?? 0} active
            </span>
          </div>

          <div className="mt-5 grid grid-cols-2 gap-x-8 gap-y-5 xl:grid-cols-4">
            {loading && summaries.length === 0
              ? Array.from({ length: 4 }, (_, index) => (
                  <div className="h-[68px] animate-pulse rounded-lg bg-canvas" key={index} />
                ))
              : summaries.map((item) => (
                  <div key={item.category}>
                    <div className="flex items-baseline justify-between gap-3">
                      <span className="truncate text-xs capitalize text-ink-600">
                        {item.category}
                      </span>
                      <span className="font-mono text-[11px] tabular-nums text-ink-400">
                        {item.utilisation_pct.toFixed(0)}%
                      </span>
                    </div>
                    <p className="mt-1.5 text-lg font-medium tabular-nums text-ink-950">
                      {money.format(item.remaining)}
                      <span className="ml-1 text-xs font-normal text-ink-400">left</span>
                    </p>
                    <div className="mt-2 h-1 overflow-hidden rounded-full bg-canvas-deep">
                      <div
                        className="h-full rounded-full bg-pactra-600"
                        style={{ width: `${Math.min(item.utilisation_pct, 100)}%` }}
                      />
                    </div>
                  </div>
                ))}
          </div>
        </div>

        <aside
          className="border-t border-line bg-canvas/55 px-5 py-5 sm:px-6 lg:border-l lg:border-t-0"
          id="policy"
        >
          <h3 className="text-sm font-medium text-ink-950">Active policy</h3>
          <dl className="mt-3 divide-y divide-line text-xs">
            <div className="flex items-center justify-between gap-4 py-2.5">
              <dt className="text-ink-500">Daily limit</dt>
              <dd className="font-mono tabular-nums text-ink-800">
                {policyAmount(policy?.daily_limit)}
              </dd>
            </div>
            <div className="flex items-center justify-between gap-4 py-2.5">
              <dt className="text-ink-500">Payment cap</dt>
              <dd className="font-mono tabular-nums text-ink-800">
                {policyAmount(policy?.per_transaction_limit)}
              </dd>
            </div>
            <div className="flex items-center justify-between gap-4 py-2.5">
              <dt className="text-ink-500">Approval above</dt>
              <dd className="font-mono tabular-nums text-ink-800">
                {policyAmount(policy?.require_approval_above)}
              </dd>
            </div>
          </dl>
        </aside>
      </div>
    </section>
  );
}
