export type TransactionStatus =
  | "draft"
  | "pending_approval"
  | "executing"
  | "completed"
  | "blocked"
  | "rejected"
  | "failed"
  | "cancelled"
  | "reversed";

export type TransactionType = "vendor_payment" | "payout" | "sandbox_transfer";
export type PaymentRail = "internal_sandbox" | "paypal_sandbox_payouts";

export interface User {
  id: string;
  email: string;
  display_name: string;
  is_demo: boolean;
  demo_expires_at: string | null;
}
export interface WalletBalance {
  currency: "USD";
  available_cents: number;
  reserved_cents: number;
  posted_cents: number;
  sandbox_generation: number;
}
export interface Policy {
  daily_limit_cents: number;
  per_transaction_limit_cents: number;
  approval_threshold_cents: number;
  allowed_categories: string[];
  category_budgets_cents: Record<string, number>;
  blocked_vendors: string[];
  currency: "USD";
}
export interface PolicyEnvelope { id: string; version: number; policy: Policy }
export interface PolicyVersion {
  id: string;
  version: number;
  policy: Policy;
  created_at: string;
}
export interface Transaction {
  id: string;
  type: TransactionType;
  vendor: string;
  recipient: string | null;
  amount_cents: number;
  currency: "USD";
  category: string;
  reason: string;
  status: TransactionStatus;
  sandbox_generation: number;
  policy_version: number;
  rail: PaymentRail;
  rail_reference: string | null;
  provider_batch_id: string | null;
  provider_item_id: string | null;
  provider_status: string | null;
  failure_code: string | null;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
}
export interface PaymentRequest {
  type: TransactionType;
  vendor: string;
  recipient: string | null;
  amount_cents: number;
  currency: "USD";
  category: string;
  reason: string;
  rail: PaymentRail;
  idempotency_key: string;
}
export interface PaymentResponse {
  transaction: Transaction;
  policy_result: Record<string, unknown>;
  balance: WalletBalance;
}
export interface PolicyPreview {
  decision: "approved" | "approval_required" | "blocked";
  reason_code: string | null;
  policy_version: number;
  checks: Array<Record<string, unknown>>;
}
export interface ApprovalItem {
  transaction: Transaction;
  requester: User;
  current_policy_decision: "approved" | "approval_required" | "blocked";
  current_policy_reason_code: string | null;
  current_policy_version: number;
  policy_checks: Array<Record<string, unknown>>;
  available_balance: WalletBalance;
}
export interface TransactionPage { items: Transaction[]; next_cursor: string | null }
export interface SpendCategory {
  category: string;
  budget_cents: number;
  committed_cents: number;
  reserved_cents: number;
  remaining_cents: number;
  utilisation_percent: number;
}
export interface SpendSummary {
  date: string;
  daily_limit_cents: number;
  daily_committed_cents: number;
  daily_reserved_cents: number;
  categories: SpendCategory[];
}
export interface LedgerItem {
  journal_id: string;
  journal_type: string;
  transaction_id: string | null;
  wallet_delta_cents: number;
  counter_account_label: string;
  created_at: string;
}
export interface LedgerPage { items: LedgerItem[]; next_cursor: string | null }
export interface TransactionDetail {
  transaction: Transaction;
  policy_checks: Array<Record<string, unknown>>;
  ledger_entries: Array<Record<string, unknown>>;
  events: Array<Record<string, unknown>>;
  attempts: Array<Record<string, unknown>>;
}
export interface AssistantResponse {
  conversation_id: string;
  reply: string;
  tool_calls: Array<Record<string, unknown>>;
  transactions_created: string[];
}
export interface ConversationMessage {
  id: string;
  role: "user" | "assistant" | "tool";
  content: string;
  tool_calls: Array<Record<string, unknown>> | null;
  created_at: string;
}
export interface ConversationSummary {
  id: string;
  title: string;
  message_count: number;
  preview: string | null;
  created_at: string;
  updated_at: string;
  archived_at: string | null;
}
export interface PayPalStatus {
  configured: boolean;
  environment: "sandbox";
  capabilities: string[];
  test_recipient_email: string | null;
  last_success_at: string | null;
  last_error_code: string | null;
}
