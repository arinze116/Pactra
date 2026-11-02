export type TransactionStatus = "approved" | "blocked" | "pending_approval";
export type TransactionType = "payment" | "payout";

export interface Transaction {
  id: string;
  timestamp: string;
  vendor: string;
  amount: number;
  currency: string;
  category: string;
  reason: string;
  status: TransactionStatus;
  block_reason: string | null;
  paypal_order_id: string | null;
  paypal_status: string | null;
  initiated_by: string;
  transaction_type: TransactionType;
}

export interface SpendSummary {
  category: string;
  budget: number;
  spent_today: number;
  remaining: number;
  utilisation_pct: number;
}

export interface Policy {
  daily_limit: number;
  per_transaction_limit: number;
  require_approval_above: number;
  approved_categories: string[];
  blocked_vendors: string[];
  budgets: Record<string, number>;
  currency: string;
}

export interface ChatHistoryMessage {
  role: "user" | "agent";
  content: string;
}

export interface ChatResponse {
  reply: string;
  tool_calls: Array<{
    name: string;
    arguments: Record<string, unknown>;
    result: Record<string, unknown>;
  }>;
  transactions_created: string[];
}
