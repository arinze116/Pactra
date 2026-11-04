import {
  Archive,
  ArrowUp,
  Bot,
  Check,
  ChevronDown,
  History,
  LoaderCircle,
  MessageSquare,
  Pencil,
  Plus,
  RotateCcw,
  ShieldCheck,
  X,
} from "lucide-react";
import {
  FormEvent,
  KeyboardEvent,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import type { ConversationMessage, ConversationSummary } from "../types";
import { ErrorNotice, formatCents } from "./UI";

function createRequestId() {
  return `assistant-${crypto.randomUUID().replace(/-/g, "")}`;
}

function conversationTime(value: string) {
  const date = new Date(value);
  const today = new Date();
  return date.toDateString() === today.toDateString()
    ? date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
    : date.toLocaleDateString([], { month: "short", day: "numeric" });
}

function actionDetails(call: Record<string, unknown>) {
  const name = String(call.name ?? "action");
  const result = call.result && typeof call.result === "object"
    ? call.result as Record<string, unknown>
    : {};
  if (typeof result.error === "string") {
    return { title: "Action could not be completed", detail: result.error, tone: "error" as const };
  }
  if (name === "create_payment_request") {
    const status = String(result.status ?? "created").replace(/_/g, " ");
    const amount = typeof result.amount_cents === "number" ? formatCents(result.amount_cents) : null;
    const completed = result.status === "completed";
    return {
      title: completed ? "Payment completed" : `Payment ${status}`,
      detail: [String(result.vendor ?? "Payment request"), amount, `Status: ${status}`].filter(Boolean).join(" · "),
      tone: completed ? "success" as const : "neutral" as const,
      transactionId: typeof result.id === "string" ? result.id : undefined,
    };
  }
  if (name === "get_wallet_summary") {
    return {
      title: "Wallet checked",
      detail: typeof result.available_cents === "number" ? `${formatCents(result.available_cents)} available` : "Available balance returned",
      tone: "success" as const,
    };
  }
  if (name === "get_policy_summary") return { title: "Policy checked", detail: `Version ${String(result.version ?? "current")}`, tone: "success" as const };
  if (name === "list_recent_transactions") return { title: "Recent activity loaded", detail: "Owner-scoped transaction history", tone: "success" as const };
  if (name === "get_transaction_details") return { title: "Receipt checked", detail: "Transaction and policy trace loaded", tone: "success" as const };
  return { title: "Validated action", detail: name.replace(/_/g, " "), tone: "neutral" as const };
}

function ActionResult({ call }: { call: Record<string, unknown> }) {
  const details = actionDetails(call);
  return <div className={`assistant-action assistant-action-${details.tone}`}>
    <span className="assistant-action-mark">{details.tone === "error" ? <X className="h-3.5 w-3.5" /> : <Check className="h-3.5 w-3.5" />}</span>
    <div className="min-w-0 flex-1">
      <p className="text-sm font-medium text-ink-950">{details.title}</p>
      <p className="mt-1 break-words text-xs leading-5 text-ink-500">{details.detail}</p>
      {details.transactionId ? <Link className="mt-2 inline-flex text-xs font-medium text-pactra-600" to={`/app/transactions/${details.transactionId}`}>Open verified receipt</Link> : null}
    </div>
  </div>;
}

function MessageItem({ message, showAssistantActions }: { message: ConversationMessage; showAssistantActions: boolean }) {
  if (message.role === "tool") {
    return <div className="space-y-2 px-4 py-2 sm:px-6">{message.tool_calls?.map((call, index) => <ActionResult call={call} key={`${message.id}-${index}`} />)}</div>;
  }
  const actions = message.role === "assistant" && showAssistantActions ? message.tool_calls ?? [] : [];
  return <article className={`assistant-message assistant-message-${message.role}`}>
    <div className="assistant-message-meta"><span>{message.role === "user" ? "You" : "Pactra"}</span><time dateTime={message.created_at}>{new Date(message.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</time></div>
    <p className="whitespace-pre-wrap break-words text-sm leading-6 text-ink-800">{message.content}</p>
    {actions.length ? <div className="mt-3 space-y-2">{actions.map((call, index) => <ActionResult call={call} key={`${message.id}-action-${index}`} />)}</div> : null}
  </article>;
}

export function AssistantWorkspace() {
  const { conversationId } = useParams();
  const navigate = useNavigate();
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [messages, setMessages] = useState<ConversationMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [pendingText, setPendingText] = useState<string | null>(null);
  const [pendingRequestId, setPendingRequestId] = useState<string | null>(null);
  const [loadingList, setLoadingList] = useState(true);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [listError, setListError] = useState("");
  const [messageError, setMessageError] = useState("");
  const [includeArchived, setIncludeArchived] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [renaming, setRenaming] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const nearBottomRef = useRef(true);

  const activeConversation = useMemo(
    () => conversations.find((item) => item.id === conversationId) ?? null,
    [conversationId, conversations],
  );

  const loadConversations = useCallback(async () => {
    setLoadingList(true);
    setListError("");
    try {
      const response = await api.conversations(includeArchived);
      setConversations(response.items);
      if (!conversationId && !includeArchived && response.items[0]) {
        navigate(`/app/assistant/${response.items[0].id}`, { replace: true });
      }
    } catch (caught) {
      setListError(caught instanceof Error ? caught.message : "Conversation history is unavailable");
    } finally {
      setLoadingList(false);
    }
  }, [conversationId, includeArchived, navigate]);

  const loadMessages = useCallback(async (id: string) => {
    setLoadingMessages(true);
    setMessageError("");
    try {
      const response = await api.conversation(id);
      nearBottomRef.current = true;
      setMessages(response.items);
    } catch (caught) {
      setMessages([]);
      setMessageError(caught instanceof Error ? caught.message : "Messages could not be loaded");
    } finally {
      setLoadingMessages(false);
    }
  }, []);

  useEffect(() => { void loadConversations(); }, [loadConversations]);
  useEffect(() => {
    if (conversationId) void loadMessages(conversationId);
    else setMessages([]);
  }, [conversationId, loadMessages]);

  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    textarea.style.height = "auto";
    textarea.style.height = `${Math.min(textarea.scrollHeight, 160)}px`;
  }, [input]);

  useEffect(() => {
    if (!nearBottomRef.current) return;
    const frame = requestAnimationFrame(() => {
      const container = scrollRef.current;
      if (!container) return;
      if (!messages.length && !pendingText) {
        container.scrollTop = 0;
        return;
      }
      container.scrollTop = container.scrollHeight;
    });
    return () => cancelAnimationFrame(frame);
  }, [messages, pendingText, sending]);

  function handleScroll() {
    const container = scrollRef.current;
    if (!container) return;
    nearBottomRef.current = container.scrollHeight - container.scrollTop - container.clientHeight < 96;
  }

  async function createNewConversation() {
    setMessageError("");
    try {
      const conversation = await api.createConversation();
      setConversations((current) => [conversation, ...current]);
      setMessages([]);
      setHistoryOpen(false);
      navigate(`/app/assistant/${conversation.id}`);
      requestAnimationFrame(() => textareaRef.current?.focus());
    } catch (caught) {
      setMessageError(caught instanceof Error ? caught.message : "Conversation could not be created");
    }
  }

  async function submitMessage(event?: FormEvent) {
    event?.preventDefault();
    const value = input.trim();
    if (!value || sending) return;
    setSending(true);
    setPendingText(value);
    setMessageError("");
    const stableRequestId = pendingRequestId ?? createRequestId();
    setPendingRequestId(stableRequestId);
    try {
      let id = conversationId;
      if (!id) {
        const created = await api.createConversation();
        id = created.id;
        navigate(`/app/assistant/${id}`, { replace: true });
      }
      await api.chat(value, id, stableRequestId);
      setInput("");
      setPendingRequestId(null);
      setPendingText(null);
      await Promise.all([loadMessages(id), loadConversations()]);
    } catch (caught) {
      setPendingText(null);
      setMessageError(caught instanceof Error ? caught.message : "The assistant could not send this message");
    } finally {
      setSending(false);
    }
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      event.currentTarget.form?.requestSubmit();
    }
  }

  async function saveRename(id: string) {
    const title = renameValue.trim();
    if (!title) return;
    try {
      const updated = await api.updateConversation(id, { title });
      setConversations((current) => current.map((item) => item.id === id ? updated : item));
      setRenaming(null);
    } catch (caught) {
      setListError(caught instanceof Error ? caught.message : "Conversation could not be renamed");
    }
  }

  async function setArchived(conversation: ConversationSummary, archived: boolean) {
    try {
      await api.updateConversation(conversation.id, { archived });
      if (conversation.id === conversationId) navigate("/app/assistant", { replace: true });
      await loadConversations();
    } catch (caught) {
      setListError(caught instanceof Error ? caught.message : "Conversation could not be updated");
    }
  }

  const hasToolMessages = messages.some((message) => message.role === "tool");

  return <div className="assistant-workspace">
    <div className="assistant-mobile-bar"><button className="action-secondary" onClick={() => setHistoryOpen((open) => !open)} type="button"><History className="h-4 w-4" />History <ChevronDown className={`h-4 w-4 transition-transform ${historyOpen ? "rotate-180" : ""}`} /></button><button className="action-primary" onClick={() => void createNewConversation()} type="button"><Plus className="h-4 w-4" />New</button></div>

    <aside className={`assistant-history ${historyOpen ? "assistant-history-open" : ""}`}>
      <div className="flex items-center justify-between border-b border-line px-4 py-4"><div><p className="text-sm font-medium text-ink-950">Conversations</p><p className="mt-1 text-xs text-ink-500">Saved to your account</p></div><button aria-label="New conversation" className="icon-button" onClick={() => void createNewConversation()} type="button"><Plus className="h-4 w-4" /></button></div>
      <div className="flex gap-1 border-b border-line p-2"><button className={`assistant-history-tab ${!includeArchived ? "assistant-history-tab-active" : ""}`} onClick={() => setIncludeArchived(false)} type="button">Active</button><button className={`assistant-history-tab ${includeArchived ? "assistant-history-tab-active" : ""}`} onClick={() => setIncludeArchived(true)} type="button">All</button></div>
      <div className="min-h-0 flex-1 overflow-y-auto p-2">
        {listError ? <div className="p-2"><ErrorNotice message={listError} onRetry={() => void loadConversations()} /></div> : null}
        {loadingList ? <div className="space-y-2 p-2">{[0, 1, 2].map((item) => <div className="loading-placeholder h-16 rounded-lg border border-line bg-canvas-deep" key={item} />)}</div> : null}
        {!loadingList && !conversations.length ? <div className="px-3 py-10 text-center"><MessageSquare className="mx-auto h-5 w-5 text-ink-400" /><p className="mt-3 text-sm text-ink-600">No saved conversations</p><button className="mt-3 text-xs font-medium text-pactra-600" onClick={() => void createNewConversation()} type="button">Start one</button></div> : null}
        <div className="space-y-1">{conversations.map((conversation) => <div className={`assistant-history-row ${conversation.id === conversationId ? "assistant-history-row-active" : ""}`} key={conversation.id}>
          {renaming === conversation.id ? <form className="p-2" onSubmit={(event) => { event.preventDefault(); void saveRename(conversation.id); }}><label className="sr-only" htmlFor={`rename-${conversation.id}`}>Conversation title</label><input autoFocus className="input h-9" id={`rename-${conversation.id}`} maxLength={120} onChange={(event) => setRenameValue(event.target.value)} value={renameValue} /><div className="mt-2 flex justify-end gap-2"><button className="text-xs text-ink-500" onClick={() => setRenaming(null)} type="button">Cancel</button><button className="text-xs font-medium text-pactra-600" type="submit">Save</button></div></form> : <><button className="min-w-0 flex-1 px-3 py-3 text-left" onClick={() => { navigate(`/app/assistant/${conversation.id}`); setHistoryOpen(false); }} type="button"><span className="block truncate text-sm font-medium text-ink-800">{conversation.title}</span><span className="mt-1 block truncate text-xs text-ink-500">{conversation.preview ?? "No messages yet"}</span><span className="mt-2 block text-[11px] text-ink-400">{conversation.message_count} messages · {conversationTime(conversation.updated_at)}</span></button><div className="flex shrink-0 items-center gap-1 pr-2"><button aria-label={`Rename ${conversation.title}`} className="icon-button-small" onClick={() => { setRenaming(conversation.id); setRenameValue(conversation.title); }} type="button"><Pencil className="h-3.5 w-3.5" /></button><button aria-label={`${conversation.archived_at ? "Restore" : "Archive"} ${conversation.title}`} className="icon-button-small" onClick={() => void setArchived(conversation, !conversation.archived_at)} type="button">{conversation.archived_at ? <RotateCcw className="h-3.5 w-3.5" /> : <Archive className="h-3.5 w-3.5" />}</button></div></>}
        </div>)}</div>
      </div>
    </aside>

    <section className="assistant-conversation">
      <header className="assistant-conversation-header"><div className="min-w-0"><p className="truncate text-sm font-medium text-ink-950">{activeConversation?.title ?? "Payment assistant"}</p><p className="mt-1 text-xs text-ink-500">Policy and ledger rules run on the server</p></div><div className="hidden items-center gap-2 text-xs text-ink-500 sm:flex"><ShieldCheck className="h-4 w-4 text-pactra-600" />Governed actions</div></header>
      <div className="assistant-message-list" onScroll={handleScroll} ref={scrollRef}>
        {messageError ? <div className="m-4 sm:m-6"><ErrorNotice message={messageError} onRetry={conversationId ? () => void loadMessages(conversationId) : undefined} /></div> : null}
        {loadingMessages ? <div className="grid h-full place-items-center text-sm text-ink-500"><span className="inline-flex items-center gap-2"><LoaderCircle className="h-4 w-4 animate-spin" />Loading conversation</span></div> : null}
        {!loadingMessages && !messages.length && !pendingText ? <div className="assistant-empty"><Bot className="h-6 w-6 text-pactra-600" /><h2>Start with a payment question</h2><p>Ask Pactra to create a governed sandbox request, check available funds, explain policy, or find a receipt.</p><div className="mt-5 grid gap-2 sm:grid-cols-2">{["Pay Linear $49 for our software subscription", "Show my available sandbox balance", "What does my current policy allow?", "List my recent transactions"].map((prompt) => <button className="assistant-prompt" key={prompt} onClick={() => { setInput(prompt); requestAnimationFrame(() => textareaRef.current?.focus()); }} type="button">{prompt}</button>)}</div></div> : null}
        {!loadingMessages ? <div className="assistant-message-stack">{messages.map((message) => <MessageItem key={message.id} message={message} showAssistantActions={!hasToolMessages} />)}{pendingText ? <article className="assistant-message assistant-message-user assistant-message-pending"><div className="assistant-message-meta"><span>You</span><span>Sending</span></div><p className="whitespace-pre-wrap break-words text-sm leading-6">{pendingText}</p></article> : null}{sending ? <div className="assistant-thinking"><LoaderCircle className="h-4 w-4 animate-spin" />Checking policy, wallet, and execution state</div> : null}</div> : null}
      </div>
      <form className="assistant-composer" onSubmit={(event) => void submitMessage(event)}><label className="sr-only" htmlFor="assistant-message">Message Pactra</label><div className="assistant-composer-box"><textarea aria-describedby="assistant-composer-help" className="assistant-textarea" disabled={sending} id="assistant-message" maxLength={8000} onChange={(event) => { setInput(event.target.value); setPendingRequestId(null); }} onKeyDown={handleKeyDown} placeholder="Ask about a payment, policy, balance, or receipt" ref={textareaRef} rows={1} value={input} /><div className="flex items-center justify-between gap-3 border-t border-line px-3 py-2"><span className="truncate text-xs text-ink-400" id="assistant-composer-help">Enter to send · Shift+Enter for a new line</span><button aria-label={sending ? "Sending message" : "Send message"} className="assistant-send" disabled={!input.trim() || sending} type="submit">{sending ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <ArrowUp className="h-4 w-4" />}</button></div></div></form>
    </section>
  </div>;
}
