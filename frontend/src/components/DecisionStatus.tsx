import type { TransactionStatus } from "../types";

interface DecisionStatusProps {
  status: TransactionStatus;
}

const config = {
  approved: {
    label: "Approved",
    dot: "bg-positive",
    text: "text-positive-dark",
  },
  blocked: {
    label: "Blocked",
    dot: "bg-negative",
    text: "text-negative",
  },
  pending_approval: {
    label: "Needs approval",
    dot: "bg-warning",
    text: "text-warning-dark",
  },
} satisfies Record<
  TransactionStatus,
  { label: string; dot: string; text: string }
>;

export function DecisionStatus({ status }: DecisionStatusProps) {
  const item = config[status];

  return (
    <span className={`inline-flex items-center gap-2 whitespace-nowrap text-xs font-medium ${item.text}`}>
      <span aria-hidden="true" className={`h-2 w-2 rounded-full ${item.dot}`} />
      {item.label}
    </span>
  );
}
