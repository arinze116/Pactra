import { Check, Clock3, ShieldX } from "lucide-react";
import type { TransactionStatus } from "../types";

interface StatusBadgeProps {
  status: TransactionStatus;
}

const config = {
  approved: {
    label: "Approved",
    className: "border-emerald-400/20 bg-emerald-400/10 text-emerald-300",
    icon: Check,
  },
  blocked: {
    label: "Blocked",
    className: "border-rose-400/20 bg-rose-400/10 text-rose-300",
    icon: ShieldX,
  },
  pending_approval: {
    label: "Needs approval",
    className: "border-amber-300/20 bg-amber-300/10 text-amber-200",
    icon: Clock3,
  },
} satisfies Record<
  TransactionStatus,
  { label: string; className: string; icon: typeof Check }
>;

export function StatusBadge({ status }: StatusBadgeProps) {
  const item = config[status];
  const Icon = item.icon;

  return (
    <span
      className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-full border px-2.5 py-1 text-[11px] font-semibold ${item.className}`}
    >
      <Icon aria-hidden="true" className="h-3 w-3" strokeWidth={2.5} />
      {item.label}
    </span>
  );
}
