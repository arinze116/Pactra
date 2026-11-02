import { FormEvent, KeyboardEvent, useEffect, useRef, useState } from "react";
import {
  ArrowUp,
  Bot,
  CheckCircle2,
  LoaderCircle,
  LockKeyhole,
  Sparkles,
  UserRound,
} from "lucide-react";
import { api } from "../api";
import type { ChatHistoryMessage } from "../types";

interface ChatProps {
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
    "Good morning, Marcus. I’m ready to handle payments within your active policy. What would you like me to take care of?",
};

const suggestions = [
  "Pay Linear $49 for our monthly software subscription",
  "Send a $125 freelance payout to ada@example.com",
  "Show me today's remaining budget",
];

export function Chat({ onTransactionCreated }: ChatProps) {
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
              : "I couldn't reach the payment service. Please try again.",
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
    <section className="flex min-h-[620px] min-w-0 flex-col overflow-hidden rounded-2xl border border-white/[0.07] bg-ink-850/70 shadow-panel lg:h-[calc(100vh-286px)] lg:min-h-[620px]">
      <header className="flex items-center justify-between border-b border-white/[0.06] px-5 py-4">
        <div className="flex items-center gap-3">
          <div className="relative grid h-9 w-9 place-items-center rounded-xl bg-gradient-to-br from-pactra-400/20 to-violet-400/10 text-pactra-300 ring-1 ring-inset ring-pactra-300/20">
            <Bot className="h-4.5 w-4.5" aria-hidden="true" />
            <span className="absolute -bottom-0.5 -right-0.5 h-2.5 w-2.5 rounded-full border-2 border-ink-850 bg-pactra-400" />
          </div>
          <div>
            <h2 className="text-sm font-semibold text-white">Pactra agent</h2>
            <p className="text-[11px] text-slate-500">Gemini-powered · policy constrained</p>
          </div>
        </div>
        <div className="flex items-center gap-1.5 rounded-full border border-white/[0.06] bg-white/[0.025] px-2.5 py-1.5 text-[10px] font-semibold uppercase tracking-[0.12em] text-slate-500">
          <LockKeyhole className="h-3 w-3 text-pactra-400" aria-hidden="true" />
          Guarded
        </div>
      </header>

      <div
        aria-live="polite"
        className="min-h-0 flex-1 space-y-5 overflow-y-auto px-4 py-5 sm:px-5"
      >
        {messages.map((message) => (
          <article
            className={`flex gap-3 ${message.role === "user" ? "flex-row-reverse" : ""}`}
            key={message.id}
          >
            <div
              className={`mt-0.5 grid h-7 w-7 shrink-0 place-items-center rounded-lg ${
                message.role === "agent"
                  ? "bg-pactra-400/10 text-pactra-300"
                  : "bg-violet-400/10 text-violet-300"
              }`}
            >
              {message.role === "agent" ? (
                <Sparkles className="h-3.5 w-3.5" aria-hidden="true" />
              ) : (
                <UserRound className="h-3.5 w-3.5" aria-hidden="true" />
              )}
            </div>
            <div className={`max-w-[84%] ${message.role === "user" ? "text-right" : ""}`}>
              <div
                className={`inline-block whitespace-pre-wrap rounded-2xl px-4 py-3 text-left text-[13px] leading-6 ${
                  message.role === "user"
                    ? "rounded-tr-sm bg-violet-500/15 text-slate-200 ring-1 ring-inset ring-violet-300/10"
                    : message.error
                      ? "rounded-tl-sm bg-rose-400/10 text-rose-200 ring-1 ring-inset ring-rose-300/15"
                      : "rounded-tl-sm bg-white/[0.04] text-slate-300 ring-1 ring-inset ring-white/[0.05]"
                }`}
              >
                {message.content}
              </div>
              {message.actionCount ? (
                <div className="mt-2 flex items-center gap-1.5 text-[10px] font-medium text-pactra-400">
                  <CheckCircle2 className="h-3 w-3" aria-hidden="true" />
                  {message.actionCount} governed action{message.actionCount === 1 ? "" : "s"} completed
                </div>
              ) : null}
            </div>
          </article>
        ))}

        {sending ? (
          <div className="flex items-center gap-3" role="status">
            <div className="grid h-7 w-7 place-items-center rounded-lg bg-pactra-400/10 text-pactra-300">
              <Sparkles className="h-3.5 w-3.5" aria-hidden="true" />
            </div>
            <div className="flex items-center gap-1.5 rounded-2xl rounded-tl-sm bg-white/[0.04] px-4 py-3 ring-1 ring-inset ring-white/[0.05]">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-slate-500" />
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-slate-500 [animation-delay:150ms]" />
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-slate-500 [animation-delay:300ms]" />
              <span className="sr-only">Pactra is evaluating the request</span>
            </div>
          </div>
        ) : null}
        <div ref={endRef} />
      </div>

      <div className="border-t border-white/[0.06] bg-ink-900/60 p-4">
        {messages.length === 1 ? (
          <div className="mb-3 flex gap-2 overflow-x-auto pb-1">
            {suggestions.map((suggestion) => (
              <button
                className="shrink-0 rounded-full border border-white/[0.07] bg-white/[0.025] px-3 py-1.5 text-[10px] font-medium text-slate-400 transition hover:border-pactra-400/25 hover:text-slate-200"
                key={suggestion}
                onClick={() => void sendMessage(suggestion)}
                type="button"
              >
                {suggestion}
              </button>
            ))}
          </div>
        ) : null}
        <form
          className="flex items-end gap-2 rounded-2xl border border-white/[0.08] bg-white/[0.035] p-2 pl-4 transition focus-within:border-pactra-400/30 focus-within:ring-2 focus-within:ring-pactra-400/5"
          onSubmit={handleSubmit}
        >
          <textarea
            aria-label="Message Pactra"
            className="max-h-28 min-h-10 flex-1 resize-none bg-transparent py-2 text-[13px] leading-5 text-white outline-none placeholder:text-slate-600"
            disabled={sending}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask Pactra to pay, send, or check…"
            rows={1}
            value={input}
          />
          <button
            aria-label="Send message"
            className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-pactra-400 text-ink-950 transition hover:bg-pactra-300 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-500"
            disabled={sending || !input.trim()}
            type="submit"
          >
            {sending ? (
              <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden="true" />
            ) : (
              <ArrowUp className="h-4 w-4" strokeWidth={2.5} aria-hidden="true" />
            )}
          </button>
        </form>
        <p className="mt-2 text-center text-[9px] tracking-wide text-slate-700">
          Every action is checked against your policy before it reaches PayPal.
        </p>
      </div>
    </section>
  );
}
