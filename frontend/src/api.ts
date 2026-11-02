import type {
  ChatHistoryMessage,
  ChatResponse,
  Policy,
  SpendSummary,
  Transaction,
} from "./types";

const configuredBaseUrl = import.meta.env.VITE_API_URL?.trim() ?? "";
const API_BASE_URL = configuredBaseUrl.replace(/\/$/, "");

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });

  if (!response.ok) {
    let message = `Request failed with status ${response.status}`;
    try {
      const payload = (await response.json()) as { detail?: string };
      if (payload.detail) message = payload.detail;
    } catch {
      // Keep the safe status-based fallback for non-JSON errors.
    }
    throw new ApiError(message, response.status);
  }

  return (await response.json()) as T;
}

export const api = {
  chat(message: string, history: ChatHistoryMessage[]) {
    return request<ChatResponse>("/api/chat", {
      method: "POST",
      body: JSON.stringify({ message, history }),
    });
  },

  transactions() {
    return request<Transaction[]>("/api/transactions?limit=250");
  },

  spendSummary() {
    return request<SpendSummary[]>("/api/spend-summary");
  },

  policy() {
    return request<Policy>("/api/policy");
  },

  approveTransaction(transactionId: string) {
    return request<Transaction>(
      `/api/policy/approve/${encodeURIComponent(transactionId)}`,
      { method: "POST" },
    );
  },
};
