import { FormEvent, KeyboardEvent, useEffect, useRef, useState } from "react";
import { ArrowUp, Bot, CheckCircle2, ShieldCheck } from "lucide-react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { ApiError, api } from "../api";
import { useAuth } from "../auth";
import { ErrorNotice, PageHeader, Panel } from "../components/UI";
import type { PayPalStatus, PaymentRail, PolicyEnvelope, TransactionType } from "../types";

const scenarioPresets: Record<
  string,
  {
    type: TransactionType;
    vendor: string;
    recipient: string;
    amount: string;
    category: string;
    reason: string;
    rail: PaymentRail;
  }
> = {
  auto: { type: "vendor_payment", vendor: "Linear", recipient: "", amount: "49.00", category: "software", reason: "Monthly software subscription", rail: "internal_sandbox" },
  approval: { type: "payout", vendor: "Ada Contractor", recipient: "ada@example.com", amount: "125.00", category: "freelance", reason: "Freelance contract work", rail: "internal_sandbox" },
  blocked: { type: "vendor_payment", vendor: "AWS", recipient: "", amount: "185.00", category: "cloud", reason: "Cloud hosting", rail: "internal_sandbox" },
  reject: { type: "payout", vendor: "Contractor", recipient: "contractor@example.com", amount: "120.00", category: "freelance", reason: "Invoice requiring review", rail: "internal_sandbox" },
  paypal: { type: "payout", vendor: "PayPal test recipient", recipient: "", amount: "25.00", category: "freelance", reason: "PayPal Sandbox payout test", rail: "paypal_sandbox_payouts" },
};

export function NewPaymentPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const scenario = searchParams.get("scenario") ?? "";
  const preset = scenarioPresets[scenario];
  const [policy, setPolicy] = useState<PolicyEnvelope | null>(null);
  const [paypal, setPaypal] = useState<PayPalStatus | null>(null);
  const [type, setType] = useState<TransactionType>(preset?.type ?? "vendor_payment");
  const [vendor, setVendor] = useState(preset?.vendor ?? "");
  const [recipient, setRecipient] = useState(preset?.recipient ?? "");
  const [amount, setAmount] = useState(preset?.amount ?? "");
  const [category, setCategory] = useState(preset?.category ?? "software");
  const [reason, setReason] = useState(preset?.reason ?? "");
  const [rail, setRail] = useState<PaymentRail>(preset?.rail ?? "internal_sandbox");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const draftKey = `pactra-payment-draft:${user?.id ?? "anonymous"}`;

  useEffect(() => {
    if (preset || !user) return;
    const stored = sessionStorage.getItem(draftKey);
    if (!stored) return;
    try {
      const draft = JSON.parse(stored) as Partial<{ type: TransactionType; vendor: string; recipient: string; amount: string; category: string; reason: string; rail: PaymentRail }>;
      if (draft.type) setType(draft.type);
      if (typeof draft.vendor === "string") setVendor(draft.vendor);
      if (typeof draft.recipient === "string") setRecipient(draft.recipient);
      if (typeof draft.amount === "string") setAmount(draft.amount);
      if (typeof draft.category === "string") setCategory(draft.category);
      if (typeof draft.reason === "string") setReason(draft.reason);
      if (draft.rail) setRail(draft.rail);
    } catch {
      sessionStorage.removeItem(draftKey);
    }
  }, [draftKey, preset, user]);

  useEffect(() => {
    if (!user) return;
    sessionStorage.setItem(draftKey, JSON.stringify({ type, vendor, recipient, amount, category, reason, rail }));
  }, [amount, category, draftKey, rail, reason, recipient, type, user, vendor]);

  useEffect(() => {
    Promise.all([api.policy(), api.paypalStatus()])
      .then(([nextPolicy, nextPayPal]) => {
        setPolicy(nextPolicy);
        setPaypal(nextPayPal);
        if (!preset) {
          setCategory((current) => nextPolicy.policy.allowed_categories.includes(current) ? current : nextPolicy.policy.allowed_categories[0] ?? "ops");
        }
        if (scenario === "paypal") {
          setRail(nextPayPal.configured ? "paypal_sandbox_payouts" : "internal_sandbox");
          setRecipient(nextPayPal.test_recipient_email ?? "");
        }
      })
      .catch((caught) => setError(caught instanceof Error ? caught.message : "Payment form unavailable"));
  }, [preset, scenario]);

  useEffect(() => {
    if (type !== "payout") setRail("internal_sandbox");
  }, [type]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    const numeric = Number(amount);
    if (!Number.isFinite(numeric) || numeric <= 0 || !/^\d+(\.\d{1,2})?$/.test(amount)) {
      setError("Enter a valid amount with no more than two decimal places");
      return;
    }
    const amountCents = Math.round(numeric * 100);
    if (policy && amountCents >= policy.policy.approval_threshold_cents && !confirming) {
      setConfirming(true);
      return;
    }
    setSubmitting(true);
    try {
      const result = await api.createPayment({
        type,
        vendor: vendor.trim(),
        recipient: type === "payout" ? recipient.trim() : null,
        amount_cents: amountCents,
        currency: "USD",
        category,
        reason: reason.trim(),
        rail,
      });
      sessionStorage.removeItem(draftKey);
      navigate(`/app/transactions/${result.transaction.id}`);
    } catch (caught) {
      if (caught instanceof ApiError) {
        const transaction = caught.details?.transaction as { id?: string } | undefined;
        if (transaction?.id) {
          sessionStorage.removeItem(draftKey);
          navigate(`/app/transactions/${transaction.id}`);
          return;
        }
        setError(caught.message);
      } else {
        setError("Payment request could not be created");
      }
    } finally {
      setSubmitting(false);
    }
  }

  const needsConfirmation = Boolean(policy) && Number(amount || 0) * 100 >= (policy?.policy.approval_threshold_cents ?? 0);

  return <>
    <PageHeader title="New payment" description="Policy and wallet checks run on the server before any sandbox funds move" />
    {error ? <div className="mb-5"><ErrorNotice message={error} /></div> : null}
    <div className="grid gap-6 xl:grid-cols-[1fr_360px]">
      <Panel className="p-5 sm:p-6">
        <form className="space-y-6" onSubmit={submit}>
          <fieldset>
            <legend className="text-sm font-medium">Request type</legend>
            <div className="mt-3 grid grid-cols-3 gap-2">
              {(["vendor_payment", "payout", "sandbox_transfer"] as TransactionType[]).map((value) => <button className={`h-10 rounded-lg border text-xs font-medium ${type === value ? "border-ink-950 bg-ink-950 text-white" : "border-line bg-white text-ink-600"}`} key={value} onClick={() => setType(value)} type="button">{value === "vendor_payment" ? "Vendor" : value === "payout" ? "Payout" : "Transfer"}</button>)}
            </div>
          </fieldset>
          <div className="grid gap-5 sm:grid-cols-2">
            <Field label="Vendor or recipient name"><input className="input" maxLength={100} onChange={(event) => setVendor(event.target.value)} required value={vendor} /></Field>
            <Field label="Amount (USD)"><input className="input tabular-nums" inputMode="decimal" onChange={(event) => setAmount(event.target.value)} placeholder="49.00" required value={amount} /></Field>
          </div>
          {type === "payout" ? <Field label="Recipient email"><div className="flex gap-2"><input className="input flex-1" onChange={(event) => setRecipient(event.target.value)} required type="email" value={recipient} />{paypal?.test_recipient_email ? <button className="rounded-lg border border-line px-3 text-xs font-medium" onClick={() => setRecipient(paypal.test_recipient_email ?? "")} type="button">Use test recipient</button> : null}</div></Field> : null}
          <div className="grid gap-5 sm:grid-cols-2">
            <Field label="Category"><select className="input" onChange={(event) => setCategory(event.target.value)} value={category}>{policy?.policy.allowed_categories.map((item) => <option key={item} value={item}>{item}</option>)}</select></Field>
            {type === "payout" && paypal?.configured ? <Field label="Execution rail"><select className="input" onChange={(event) => setRail(event.target.value as PaymentRail)} value={rail}><option value="internal_sandbox">Internal sandbox</option><option value="paypal_sandbox_payouts">PayPal Sandbox Payouts</option></select></Field> : <Field label="Execution rail"><div className="input flex items-center text-sm text-ink-600">Internal sandbox</div></Field>}
          </div>
          <Field label="Business reason"><textarea className="input min-h-28 resize-y py-3" maxLength={500} onChange={(event) => setReason(event.target.value)} required value={reason} /></Field>
          {confirming ? <div className="rounded-xl border border-warning/30 bg-warning-soft p-4"><p className="text-sm font-medium text-warning-dark">Confirm request for {vendor || "this recipient"}</p><p className="mt-1 text-xs leading-5 text-ink-600">${Number(amount).toFixed(2)} will be submitted to the policy engine. Requests above the approval threshold reserve funds and wait for review.</p></div> : null}
          <button className="h-11 rounded-lg bg-ink-950 px-5 text-sm font-medium text-white disabled:opacity-50" disabled={submitting} type="submit">{submitting ? "Applying policy" : confirming ? "Confirm and create request" : needsConfirmation ? "Review request" : "Create payment request"}</button>
        </form>
      </Panel>
      <aside className="space-y-4">
        <Panel className="p-5"><div className="flex items-center gap-2 text-sm font-medium"><ShieldCheck className="h-4 w-4 text-pactra-700" />Decision order</div><ol className="policy-trace mt-5 space-y-4 text-xs text-ink-600">{["Account and category", "Vendor and payment cap", "Daily and category budgets", "Available wallet funds", "Approval threshold"].map((item, index) => <li className="flex items-center gap-3" key={item}><span>{index + 1}</span>{item}</li>)}</ol></Panel>
        <Panel className="p-5"><p className="text-sm font-medium">Rail disclosure</p><p className="mt-2 text-xs leading-5 text-ink-500">Internal payments use Pactra's simulated ledger. PayPal Sandbox payouts are sent by the configured sandbox business account. The balances are not linked.</p><p className={`mt-4 text-xs font-medium ${paypal?.configured ? "text-positive-dark" : "text-ink-500"}`}>{paypal?.configured ? "PayPal Sandbox configured" : "PayPal Sandbox unavailable"}</p><Link className="mt-3 inline-flex text-xs font-medium text-ink-700 underline decoration-line underline-offset-4" to="/app/settings/integrations/paypal">Integration details</Link></Panel>
      </aside>
    </div>
  </>;
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return <label className="block text-sm font-medium text-ink-800">{label}<div className="mt-2">{children}</div></label>;
}

interface UiMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  actions?: number;
  transactionId?: string;
}

export function AssistantPage() {
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<UiMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sending]);

  async function send() {
    const value = input.trim();
    if (!value || sending) return;
    setMessages((current) => [...current, { id: crypto.randomUUID(), role: "user", content: value }]);
    setInput("");
    setSending(true);
    setError("");
    try {
      const response = await api.chat(value, conversationId);
      setConversationId(response.conversation_id);
      setMessages((current) => [...current, { id: crypto.randomUUID(), role: "assistant", content: response.reply, actions: response.tool_calls.length, transactionId: response.transactions_created[0] }]);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Assistant unavailable");
    } finally {
      setSending(false);
    }
  }

  function keyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void send();
    }
  }

  return <>
    <PageHeader title="Payment assistant" description="Natural-language requests use the same policy and ledger service as the manual form" />
    {error ? <div className="mb-5"><ErrorNotice message={error} /></div> : null}
    <Panel className="mx-auto flex min-h-[620px] max-w-4xl flex-col overflow-hidden">
      <div className="flex items-center justify-between border-b border-line px-5 py-4"><div className="flex items-center gap-2 text-sm font-medium"><Bot className="h-4 w-4" />Pactra assistant</div><span className="text-xs text-ink-500">Server-side policy enforced</span></div>
      <div className="min-h-0 flex-1 overflow-y-auto">
        {messages.length ? <div className="divide-y divide-line">{messages.map((message) => <article className="px-5 py-5 sm:px-6" key={message.id}><div className="flex items-center justify-between"><p className="text-xs font-medium text-ink-500">{message.role === "user" ? "You" : "Pactra"}</p>{message.actions ? <span className="flex items-center gap-1 text-xs text-positive-dark"><CheckCircle2 className="h-3.5 w-3.5" />{message.actions} validated action{message.actions === 1 ? "" : "s"}</span> : null}</div><p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-ink-800">{message.content}</p>{message.transactionId ? <Link className="mt-3 inline-flex text-xs font-medium text-ink-950 underline decoration-line underline-offset-4" to={`/app/transactions/${message.transactionId}`}>Open transaction receipt</Link> : null}</article>)}</div> : <div className="grid min-h-[390px] place-items-center p-6 text-center"><div><Bot className="mx-auto h-6 w-6 text-ink-400" /><p className="mt-4 text-sm font-medium">Describe a sandbox payment</p><p className="mt-2 max-w-md text-sm leading-6 text-ink-500">Try “Pay Linear $49 for our monthly software subscription” or ask for your wallet balance.</p><Link className="mt-4 inline-flex text-sm font-medium text-ink-950 underline decoration-line underline-offset-4" to="/app/payments/new">Use the payment form</Link></div></div>}
        {sending ? <div className="border-t border-line px-5 py-4 text-xs text-ink-500">Checking the request against your policy</div> : null}
        <div ref={endRef} />
      </div>
      <div className="border-t border-line bg-canvas/50 p-4"><div className="rounded-xl border border-line bg-white p-2 focus-within:border-pactra-600"><textarea className="min-h-24 w-full resize-none bg-transparent px-2 py-2 text-sm outline-none" disabled={sending} maxLength={8000} onChange={(event) => setInput(event.target.value)} onKeyDown={keyDown} placeholder="Enter a payment or wallet request" value={input} /><div className="flex items-center justify-between px-2 pb-1"><span className="text-xs text-ink-400">Shift + Enter for a new line</span><button aria-label="Send message" className="grid h-9 w-9 place-items-center rounded-lg bg-ink-950 text-white disabled:opacity-40" disabled={!input.trim() || sending} onClick={() => void send()} type="button"><ArrowUp className="h-4 w-4" /></button></div></div></div>
    </Panel>
  </>;
}
