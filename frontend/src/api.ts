import type {
  AssistantResponse,
  ApprovalItem,
  ConversationMessage,
  ConversationSummary,
  LedgerPage,
  PayPalStatus,
  PaymentRequest,
  PaymentResponse,
  PolicyPreview,
  Policy,
  PolicyEnvelope,
  PolicyVersion,
  SpendSummary,
  Transaction,
  TransactionDetail,
  TransactionPage,
  User,
  WalletBalance,
} from "./types";

const API_BASE_URL = (import.meta.env.VITE_API_URL?.trim() ?? "").replace(/\/$/, "");
let csrfTokenValue: string | null = null;

interface ErrorPayload {
  error?: { code?: string; message?: string; request_id?: string; details?: Record<string, unknown> };
}

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly code = "REQUEST_FAILED",
    public readonly details?: Record<string, unknown>,
    public readonly requestId?: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function cacheCsrfToken(response: Response) {
  const token = response.headers.get("X-CSRF-Token")?.trim();
  if (token) csrfTokenValue = token;
}

interface PactraRequestInit extends RequestInit {
  timeoutMs?: number;
}

const DEFAULT_REQUEST_TIMEOUT_MS = 15_000;

async function request<T>(path: string, init: PactraRequestInit = {}): Promise<T> {
  const { timeoutMs = DEFAULT_REQUEST_TIMEOUT_MS, signal, ...requestInit } = init;
  const method = (init.method ?? "GET").toUpperCase();
  const token = method === "GET" || method === "HEAD" ? null : csrfTokenValue;
  const requestId = `web-${crypto.randomUUID().replace(/-/g, "")}`;
  const controller = new AbortController();
  const abortFromCaller = () => controller.abort(signal?.reason);
  signal?.addEventListener("abort", abortFromCaller, { once: true });
  const timeout = window.setTimeout(() => controller.abort("timeout"), timeoutMs);
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...requestInit,
      credentials: "include",
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        "X-Request-ID": requestId,
        ...(token ? { "X-CSRF-Token": token } : {}),
        ...requestInit.headers,
      },
    });
  } catch (error) {
    if (controller.signal.aborted && !signal?.aborted) {
      throw new Error(`Request timed out. Reference ${requestId}.`);
    }
    throw error;
  } finally {
    window.clearTimeout(timeout);
    signal?.removeEventListener("abort", abortFromCaller);
  }
  cacheCsrfToken(response);
  if (!response.ok) {
    let payload: ErrorPayload = {};
    try { payload = (await response.json()) as ErrorPayload; } catch { /* safe fallback */ }
    if (response.status === 401 && payload.error?.code === "UNAUTHENTICATED") {
      csrfTokenValue = null;
      window.dispatchEvent(new Event("pactra:unauthenticated"));
    }
    throw new ApiError(
      payload.error?.message ?? `Request failed with status ${response.status}`,
      response.status,
      payload.error?.code,
      payload.error?.details,
      payload.error?.request_id ?? response.headers.get("X-Request-ID") ?? requestId,
    );
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export function createIdempotencyKey(prefix: string) {
  return `${prefix}-${crypto.randomUUID().replace(/-/g, "")}`;
}

export function isAmbiguousMutationError(error: unknown) {
  return !(error instanceof ApiError) || error.status >= 500;
}

export const api = {
  register: (email: string, password: string) => request<{ user: User; wallet: WalletBalance }>("/api/auth/register", { method: "POST", body: JSON.stringify({ email, password }) }),
  login: (email: string, password: string) => request<{ user: User }>("/api/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }),
  session: () => request<{ user: User | null }>("/api/auth/session"),
  me: () => request<{ user: User }>("/api/auth/me"),
  logout: async () => {
    await request<void>("/api/auth/logout", { method: "POST" });
    csrfTokenValue = null;
  },
  changePassword: (currentPassword: string, newPassword: string) => request<void>("/api/auth/change-password", { method: "POST", body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }) }),
  wallet: () => request<WalletBalance>("/api/wallet"),
  ledger: () => request<LedgerPage>("/api/wallet/ledger?limit=100"),
  topUp: (amount_cents: number, idempotency_key = createIdempotencyKey("topup")) => request<{ balance: WalletBalance }>("/api/wallet/topups", { method: "POST", body: JSON.stringify({ amount_cents, idempotency_key }) }),
  resetSandbox: (idempotency_key = createIdempotencyKey("reset")) => request<{ balance_cents: number; sandbox_generation: number }>("/api/wallet/reset", { method: "POST", body: JSON.stringify({ confirmation: "RESET", idempotency_key }) }),
  startGuidedTest: () => request<{ started: boolean; sandbox_generation: number }>("/api/judge/guided/start", { method: "POST" }),
  runInsufficientFundsScenario: (idempotency_key = createIdempotencyKey("guided-insufficient")) => request<PaymentResponse>("/api/judge/scenarios/insufficient-funds", { method: "POST", body: JSON.stringify({ idempotency_key }) }),
  policy: () => request<PolicyEnvelope>("/api/policy"),
  policyHistory: () => request<{ items: PolicyVersion[] }>("/api/policies"),
  savePolicy: (policy: Policy) => request<PolicyEnvelope>("/api/policy", { method: "PUT", body: JSON.stringify(policy) }),
  resetPolicy: () => request<PolicyEnvelope>("/api/policy/reset", { method: "POST" }),
  spendSummary: () => request<SpendSummary>("/api/spend-summary"),
  transactions: (query = "") => request<TransactionPage>(`/api/transactions${query ? `?${query}` : ""}`),
  transaction: (id: string) => request<TransactionDetail>(`/api/transactions/${encodeURIComponent(id)}`),
  previewPayment: (payload: Pick<PaymentRequest, "vendor" | "amount_cents" | "currency" | "category">) => request<PolicyPreview>("/api/transactions/preview", { method: "POST", body: JSON.stringify(payload) }),
  createPayment: (payload: Omit<PaymentRequest, "idempotency_key">, idempotency_key = createIdempotencyKey("payment")) => request<PaymentResponse>("/api/transactions", { method: "POST", body: JSON.stringify({ ...payload, idempotency_key }) }),
  approvals: () => request<{ items: ApprovalItem[] }>("/api/approvals"),
  approve: (id: string, idempotency_key = createIdempotencyKey("approve")) => request<Transaction>(`/api/approvals/${encodeURIComponent(id)}/approve`, { method: "POST", body: JSON.stringify({ idempotency_key }) }),
  reject: (id: string, reason: string, idempotency_key = createIdempotencyKey("reject")) => request<Transaction>(`/api/approvals/${encodeURIComponent(id)}/reject`, { method: "POST", body: JSON.stringify({ reason, idempotency_key }) }),
  retry: (id: string, idempotency_key = createIdempotencyKey("retry")) => request<{ transaction: Transaction }>(`/api/transactions/${encodeURIComponent(id)}/retry`, { method: "POST", body: JSON.stringify({ idempotency_key }) }),
  reverse: (id: string, reason: string, idempotency_key = createIdempotencyKey("reverse")) => request<{ transaction: Transaction }>(`/api/transactions/${encodeURIComponent(id)}/reverse`, { method: "POST", body: JSON.stringify({ reason, idempotency_key }) }),
  reconcile: (id: string) => request<Transaction>(`/api/transactions/${encodeURIComponent(id)}/reconcile`, { method: "POST" }),
  chat: (message: string, conversation_id: string | null, request_id: string) => request<AssistantResponse>("/api/chat", { method: "POST", body: JSON.stringify({ message, conversation_id, request_id }), timeoutMs: 35_000 }),
  conversations: (includeArchived = false) => request<{ items: ConversationSummary[] }>(`/api/conversations${includeArchived ? "?include_archived=true" : ""}`),
  createConversation: (title?: string) => request<ConversationSummary>("/api/conversations", { method: "POST", body: JSON.stringify({ title }) }),
  updateConversation: (id: string, changes: { title?: string; archived?: boolean }) => request<ConversationSummary>(`/api/conversations/${encodeURIComponent(id)}`, { method: "PATCH", body: JSON.stringify(changes) }),
  conversation: (id: string) => request<{ items: ConversationMessage[] }>(`/api/conversations/${encodeURIComponent(id)}/messages`),
  paypalStatus: () => request<PayPalStatus>("/api/integrations/paypal/status"),
};
