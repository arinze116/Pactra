import { FormEvent, KeyboardEvent, useEffect, useRef, useState } from "react";
import {
  ArrowUp,
  CheckCircle2,
  CornerDownRight,
  LoaderCircle,
  LockKeyhole,
  ShieldCheck,
  UserRound,
} from "lucide-react";
import { api } from "../api";
import type { ChatHistoryMessage } from "../types";

interface PaymentAgentProps {
  onTransactionCreated: () => Promise<void> | void;
}

interface UiMessage {
  id: string;
  role: "user" | "agent";
  content: string;
  error?: boolean;
  actionCount?: number;
}

const starterMessage: UiMessage = {
  id: "welcome",
  role: "agent",
  content:
    "Payment operations are ready. Describe a payment or ask for today’s remaining budget.",
};

const suggestions = [
  "Pay Linear $49 for our monthly software subscription",
  "Send a $125 freelance payout to ada@example.com",
  "Show me today’s remaining budget",
];

export function PaymentAgent({ onTransactionCreated }: PaymentAgentProps) {
  const [messages, setMessages] = useState<UiMessage[]>([starterMessage]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [messages, sending]);

  async function sendMessage(rawMessage: string) {
    const message = rawMessage.trim();
    if (!message || sending) return;

    const history: ChatHistoryMessage[] = messages.map(({ role, content }) => ({
      role,
      content,
    }));
    const userMessage: UiMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: message,
    };

    setMessages((current) => [...current, userMessage]);
    setInput("");
    setSending(true);

    try {
      const response = await api.chat(message, history);
      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          role: "agent",
          content: response.reply,
          actionCount: response.tool_calls.length,
        },
      ]);
      if (response.transactions_created.length > 0) {
        await onTransactionCreated();
      }
    } catch (error) {
      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          role: "agent",
          content:
            error instanceof Error
              ? error.message
              : "The payment service could not be reached. Try again.",
          error: true,
        },
      ]);
    } finally {
      setSending(false);
    }
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    void sendMessage(input);
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void sendMessage(input);
    }
  }

  return (
    <section
      aria-labelledby="agent-title"
      className="flex min-h-[560px] min-w-0 flex-col overflow-hidden rounded-2xl border border-line bg-white shadow-card"
      id="agent"
    >
      <header className="flex items-start justify-between gap-4 border-b border-line px-5 py-5 sm:px-6">
        <div className="flex items-center gap-3">
          <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-pactra-50 text-pactra-700">
            <ShieldCheck aria-hidden="true" className="h-5 w-5" strokeWidth={1.5} />
          </span>
          <div>
            <h2 className="text-sm font-medium text-ink-950" id="agent-title">
              Payment agent
            </h2>
            <p className="mt-1 text-xs text-ink-500">Gemini interprets, policy decides</p>
          </div>
        </div>
        <div className="flex items-center gap-2 text-xs text-ink-500">
          <LockKeyhole
            aria-hidden="true"
            className="h-3.5 w-3.5 text-pactra-700"
            strokeWidth={1.5}
          />
          Guarded
        </div>
      </header>

      <div aria-live="polite" className="min-h-0 flex-1 space-y-5 overflow-y-auto px-5 py-6">
        {messages.map((message) => (
          <article
            className={`flex gap-3 ${message.role === "user" ? "flex-row-reverse" : ""}`}
            key={message.id}
          >
            <span
              className={`mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-lg ${
                message.role === "agent"
                  ? "bg-pactra-50 text-pactra-700"
                  : "bg-canvas-deep text-ink-600"
              }`}
            >
              {message.role === "agent" ? (
                <ShieldCheck aria-hidden="true" className="h-4 w-4" strokeWidth={1.5} />
              ) : (
                <UserRound aria-hidden="true" className="h-4 w-4" strokeWidth={1.5} />
              )}
            </span>
            <div className={`max-w-[84%] ${message.role === "user" ? "text-right" : ""}`}>
              <div
                className={`inline-block whitespace-pre-wrap rounded-xl px-4 py-3 text-left text-sm leading-6 ${
                  message.role === "user"
                    ? "bg-ink-950 text-white"
                    : message.error
                      ? "border border-negative/15 bg-negative-soft text-negative"
                      : "border border-line bg-canvas text-ink-800"
                }`}
              >
                {message.content}
              </div>
              {message.actionCount ? (
                <div className="mt-2 flex items-center gap-2 text-xs font-medium text-pactra-700">
                  <CheckCircle2 aria-hidden="true" className="h-3.5 w-3.5" strokeWidth={1.5} />
                  {message.actionCount} governed action{message.actionCount === 1 ? "" : "s"} completed
                </div>
              ) : null}
            </div>
          </article>
        ))}

        {sending ? (
          <div className="flex items-center gap-3" role="status">
            <span className="grid h-8 w-8 place-items-center rounded-lg bg-pactra-50 text-pactra-700">
              <ShieldCheck aria-hidden="true" className="h-4 w-4" strokeWidth={1.5} />
            </span>
            <div className="flex items-center gap-2 rounded-xl border border-line bg-canvas px-4 py-3 text-xs text-ink-500">
              <LoaderCircle aria-hidden="true" className="h-3.5 w-3.5 animate-spin" />
              Evaluating policy
            </div>
          </div>
        ) : null}
        <div ref={endRef} />
      </div>

      <div className="border-t border-line bg-canvas/60 p-4 sm:p-5">
        {messages.length === 1 ? (
          <div className="mb-4 grid gap-2">
            {suggestions.map((suggestion) => (
              <button
                className="flex min-h-10 items-center gap-3 rounded-lg border border-line bg-white px-3 py-2 text-left text-xs leading-5 text-ink-600 transition-colors duration-150 hover:border-ink-300 hover:text-ink-950"
                key={suggestion}
                onClick={() => void sendMessage(suggestion)}
                type="button"
              >
                <CornerDownRight
                  aria-hidden="true"
                  className="h-3.5 w-3.5 shrink-0 text-ink-400"
                  strokeWidth={1.5}
                />
                {suggestion}
              </button>
            ))}
          </div>
        ) : null}
        <form
          className="flex items-end gap-2 rounded-xl border border-line bg-white p-2 pl-4 focus-within:border-pactra-600 focus-within:ring-2 focus-within:ring-pactra-100"
          onSubmit={handleSubmit}
        >
          <textarea
            aria-label="Message Pactra"
            className="max-h-28 min-h-10 flex-1 resize-none bg-transparent py-2 text-sm leading-5 text-ink-950 outline-none placeholder:text-ink-400"
            disabled={sending}
            maxLength={2000}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Describe a payment or ask about budget"
            rows={1}
            value={input}
          />
          <button
            aria-label="Send message"
            className="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-ink-950 text-white transition-colors duration-150 hover:bg-ink-800 disabled:cursor-not-allowed disabled:bg-ink-300"
            disabled={sending || !input.trim()}
            type="submit"
          >
            {sending ? (
              <LoaderCircle aria-hidden="true" className="h-4 w-4 animate-spin" />
            ) : (
              <ArrowUp aria-hidden="true" className="h-4 w-4" strokeWidth={1.75} />
            )}
          </button>
        </form>
        <p className="mt-2 text-center text-xs text-ink-400">
          Requests are checked against policy before PayPal receives them
        </p>
      </div>
    </section>
  );
}
