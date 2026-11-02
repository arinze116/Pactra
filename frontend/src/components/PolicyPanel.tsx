import { Cloud, Code2, Gauge, Settings2, UsersRound, Wrench } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { Policy, SpendSummary } from "../types";

interface PolicyPanelProps {
  policy: Policy | null;
  summaries: SpendSummary[];
  loading: boolean;
}

const categoryMeta: Record<
  string,
  { icon: LucideIcon; accent: string; track: string }
> = {
  ops: { icon: Wrench, accent: "bg-cyan-300", track: "bg-cyan-300/10" },
  software: { icon: Code2, accent: "bg-violet-300", track: "bg-violet-300/10" },
  cloud: { icon: Cloud, accent: "bg-sky-300", track: "bg-sky-300/10" },
  freelance: { icon: UsersRound, accent: "bg-pactra-300", track: "bg-pactra-300/10" },
};

const money = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});

export function PolicyPanel({ policy, summaries, loading }: PolicyPanelProps) {
  const totalSpent = summaries.reduce((sum, item) => sum + item.spent_today, 0);
  const dailyLimit = policy?.daily_limit ?? 0;
  const dailyUtilisation = dailyLimit ? Math.min((totalSpent / dailyLimit) * 100, 100) : 0;

  return (
    <section
      aria-label="Active spending policy"
      className="border-b border-white/[0.06] bg-white/[0.015] px-4 py-4 sm:px-6 lg:px-8"
    >
      <div className="mx-auto grid min-w-0 max-w-[1800px] gap-3 xl:grid-cols-[1.15fr_3fr]">
        <div className="flex min-h-[112px] items-center gap-4 rounded-2xl border border-white/[0.07] bg-ink-850/80 p-4 shadow-glow">
          <div className="grid h-11 w-11 shrink-0 place-items-center rounded-xl border border-pactra-400/20 bg-pactra-400/10 text-pactra-300">
            <Gauge className="h-5 w-5" aria-hidden="true" />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">
                  Daily governance
                </p>
                <p className="mt-1 text-xl font-semibold tracking-tight text-white">
                  {money.format(totalSpent)}
                  <span className="text-sm font-medium text-slate-500">
                    {" "}/ {money.format(dailyLimit)}
                  </span>
                </p>
              </div>
              <span className="rounded-lg bg-white/[0.04] px-2 py-1 text-xs font-medium text-slate-400">
                {dailyUtilisation.toFixed(0)}%
              </span>
            </div>
            <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-white/[0.06]">
              <div
                className="h-full rounded-full bg-gradient-to-r from-pactra-500 to-pactra-300 transition-[width] duration-500"
                style={{ width: `${dailyUtilisation}%` }}
              />
            </div>
            <div className="mt-2 flex items-center gap-2 text-[11px] text-slate-500">
              <Settings2 className="h-3 w-3" aria-hidden="true" />
              <span>
                Auto-pay to {money.format(policy?.require_approval_above ?? 0)} · hard cap {money.format(policy?.per_transaction_limit ?? 0)}
              </span>
            </div>
          </div>
        </div>

        <div className="grid min-w-0 grid-cols-2 gap-3 lg:grid-cols-4">
          {loading && summaries.length === 0
            ? Array.from({ length: 4 }, (_, index) => (
                <div
                  className="h-[112px] animate-pulse rounded-2xl border border-white/[0.06] bg-white/[0.025]"
                  key={index}
                />
              ))
            : summaries.map((item) => {
                const meta = categoryMeta[item.category] ?? categoryMeta.ops;
                const Icon = meta.icon;
                const percentage = Math.min(item.utilisation_pct, 100);
                return (
                  <div
                    className="rounded-2xl border border-white/[0.07] bg-ink-850/70 p-3.5 transition-colors hover:border-white/[0.12]"
                    key={item.category}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <span className={`grid h-7 w-7 place-items-center rounded-lg ${meta.track}`}>
                          <Icon className="h-3.5 w-3.5 text-slate-300" aria-hidden="true" />
                        </span>
                        <span className="text-xs font-semibold capitalize text-slate-300">
                          {item.category}
                        </span>
                      </div>
                      <span className="text-[10px] font-medium text-slate-600">
                        {item.utilisation_pct.toFixed(0)}%
                      </span>
                    </div>
                    <p className="mt-3 text-base font-semibold text-white">
                      {money.format(item.remaining)}
                      <span className="ml-1 text-[10px] font-medium text-slate-600">left</span>
                    </p>
                    <div className={`mt-2.5 h-1 overflow-hidden rounded-full ${meta.track}`}>
                      <div
                        className={`h-full rounded-full ${meta.accent} transition-[width] duration-500`}
                        style={{ width: `${percentage}%` }}
                      />
                    </div>
                  </div>
                );
              })}
        </div>
      </div>
    </section>
  );
}
