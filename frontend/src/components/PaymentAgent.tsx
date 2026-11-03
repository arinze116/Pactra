import { FormEvent, KeyboardEvent, useEffect, useRef, useState } from "react";
import {
  ArrowUp,
  CheckCircle2,
  Command,
  LoaderCircle,
  ShieldCheck,
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

export function PaymentAgent({ onTransactionCreated }: PaymentAgentProps) {
  const [messages, setMessages] = useState<UiMessage[]>([]);
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
      <header className="flex items-center justify-between gap-4 border-b border-line px-5 py-4">
        <div className="flex items-center gap-3">
          <Command aria-hidden="true" className="h-4 w-4 text-ink-500" strokeWidth={1.5} />
          <h2 className="text-sm font-medium text-ink-950" id="agent-title">
            New payment
          </h2>
        </div>
        <span className="flex items-center gap-1.5 text-xs text-ink-500">
          <ShieldCheck aria-hidden="true" className="h-3.5 w-3.5 text-pactra-700" strokeWidth={1.5} />
          Enforced
        </span>
      </header>

      <div aria-live="polite" className="min-h-0 flex-1 overflow-y-auto">
        {messages.length === 0 && !sending ? (
          <div className="grid min-h-[300px] place-items-center px-6 text-center">
            <div>
              <span className="mx-auto grid h-10 w-10 place-items-center rounded-xl bg-pactra-50 text-pactra-700">
                <ShieldCheck aria-hidden="true" className="h-5 w-5" strokeWidth={1.5} />
              </span>
              <p className="mt-4 text-sm font-medium text-ink-800">Enter a payment instruction</p>
              <p className="mx-auto mt-2 max-w-[260px] text-xs leading-5 text-ink-500">
                Each request is checked before it can reach PayPal
              </p>
            </div>
          </div>
        ) : (
          <div className="divide-y divide-line">
            {messages.map((message) => (
              <article className="px-5 py-4" key={message.id}>
                <div className="flex items-center justify-between gap-3">
                  <p className="text-xs font-medium text-ink-500">
                    {message.role === "user" ? "Instruction" : "Decision"}
                  </p>
                  {message.actionCount ? (
                    <span className="flex items-center gap-1.5 text-[11px] text-positive-dark">
                      <CheckCircle2
                        aria-hidden="true"
                        className="h-3.5 w-3.5"
                        strokeWidth={1.5}
                      />
                      {message.actionCount} action{message.actionCount === 1 ? "" : "s"}
                    </span>
                  ) : null}
                </div>
                <p
                  className={`mt-2 whitespace-pre-wrap text-sm leading-6 ${
                    message.error ? "text-negative" : "text-ink-800"
                  }`}
                >
                  {message.content}
                </p>
              </article>
            ))}

            {sending ? (
              <div className="flex items-center gap-2 px-5 py-4 text-xs text-ink-500" role="status">
                <LoaderCircle
                  aria-hidden="true"
                  className="h-4 w-4 animate-spin text-pactra-700"
                />
                Checking policy and payment details
              </div>
            ) : null}
          </div>
        )}
        <div ref={endRef} />
      </div>

      <form className="border-t border-line bg-canvas/45 p-4" onSubmit={handleSubmit}>
        <label className="text-xs font-medium text-ink-600" htmlFor="payment-instruction">
          Instruction
        </label>
        <div className="mt-2 rounded-xl border border-line bg-white p-2 focus-within:border-pactra-600 focus-within:ring-2 focus-within:ring-pactra-100">
          <textarea
            className="max-h-32 min-h-[84px] w-full resize-none bg-transparent px-2 py-2 text-sm leading-6 text-ink-950 outline-none placeholder:text-ink-400"
            disabled={sending}
            id="payment-instruction"
            maxLength={2000}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Enter payment or budget request"
            rows={3}
            value={input}
          />
          <div className="flex items-center justify-between gap-3 px-2 pb-1">
            <span className="text-[11px] text-ink-400">Shift + Enter for a new line</span>
            <button
              className="flex h-9 items-center gap-2 rounded-lg bg-ink-950 px-3.5 text-xs font-medium text-white transition-colors duration-150 hover:bg-ink-800 disabled:cursor-not-allowed disabled:bg-ink-300"
              disabled={sending || !input.trim()}
              type="submit"
            >
              {sending ? (
                <LoaderCircle aria-hidden="true" className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <ArrowUp aria-hidden="true" className="h-3.5 w-3.5" strokeWidth={1.75} />
              )}
              Submit
            </button>
          </div>
        </div>
      </form>
    </section>
  );
}
