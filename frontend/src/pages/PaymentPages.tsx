import { FormEvent, useEffect, useRef, useState } from "react";
import { ShieldCheck } from "lucide-react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { ApiError, api, createIdempotencyKey, isAmbiguousMutationError } from "../api";
import { useAuth } from "../auth";
import { AssistantWorkspace } from "../components/AssistantWorkspace";
import { ErrorNotice, PageHeader, Panel } from "../components/UI";
import type { PayPalStatus, PaymentRail, PaymentRequest, PolicyEnvelope, PolicyPreview, TransactionType } from "../types";

type PaymentPayload = Omit<PaymentRequest, "idempotency_key">;

interface PendingPaymentAttempt {
  key: string;
  digest: string;
}

async function paymentPayloadDigest(payload: PaymentPayload) {
  const canonical = JSON.stringify({
    type: payload.type,
    vendor: payload.vendor,
    recipient: payload.recipient,
    amount_cents: payload.amount_cents,
    currency: payload.currency,
    category: payload.category,
    reason: payload.reason,
    rail: payload.rail,
  });
  const bytes = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(canonical));
  return Array.from(new Uint8Array(bytes), (value) => value.toString(16).padStart(2, "0")).join("");
}

function readPendingPaymentAttempt(storageKey: string): PendingPaymentAttempt | null {
  try {
    const stored = sessionStorage.getItem(storageKey);
    if (!stored) return null;
    const parsed = JSON.parse(stored) as Partial<PendingPaymentAttempt>;
    return typeof parsed.key === "string" && typeof parsed.digest === "string"
      ? { key: parsed.key, digest: parsed.digest }
      : null;
  } catch {
    return null;
  }
}

function writePendingPaymentAttempt(storageKey: string, attempt: PendingPaymentAttempt) {
  try { sessionStorage.setItem(storageKey, JSON.stringify(attempt)); } catch { /* in-memory retry still works */ }
}

function removePendingPaymentAttempt(storageKey: string) {
  try { sessionStorage.removeItem(storageKey); } catch { /* storage may be unavailable */ }
}

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
  const [rail, setRail] = useState<PaymentRail>(scenario === "paypal" ? "internal_sandbox" : preset?.rail ?? "internal_sandbox");
  const [error, setError] = useState("");
  const [paypalError, setPaypalError] = useState("");
  const [policyLoading, setPolicyLoading] = useState(true);
  const [paypalLoading, setPaypalLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [preview, setPreview] = useState<PolicyPreview | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState("");
  const [draftHydrated, setDraftHydrated] = useState(false);
  const paymentAttemptRef = useRef<PendingPaymentAttempt | null>(null);
  const guidedInsufficientKeyRef = useRef<string | null>(null);
  const draftKey = `pactra-payment-draft:${user?.id ?? "anonymous"}`;
  const attemptKey = `pactra-payment-attempt:${user?.id ?? "anonymous"}`;

  useEffect(() => {
    setDraftHydrated(false);
    if (!user) return;
    if (preset) {
      setDraftHydrated(true);
      return;
    }
    const stored = sessionStorage.getItem(draftKey);
    if (!stored) {
      setDraftHydrated(true);
      return;
    }
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
    setDraftHydrated(true);
  }, [draftKey, preset, user]);

  useEffect(() => {
    if (!user || !draftHydrated) return;
    sessionStorage.setItem(draftKey, JSON.stringify({ type, vendor, recipient, amount, category, reason, rail }));
  }, [amount, category, draftHydrated, draftKey, rail, reason, recipient, type, user, vendor]);

  useEffect(() => {
    let active = true;
    setPolicyLoading(true);
    setPaypalLoading(true);
    setPaypalError("");
    if (scenario === "paypal") setRail("internal_sandbox");

    api.policy()
      .then((nextPolicy) => {
        if (!active) return;
        setPolicy(nextPolicy);
        if (!preset) {
          setCategory((current) => nextPolicy.policy.allowed_categories.includes(current) ? current : nextPolicy.policy.allowed_categories[0] ?? "ops");
        }
      })
      .catch((caught) => {
        if (!active) return;
        setPolicy(null);
        setError(caught instanceof Error ? caught.message : "Payment form unavailable");
      })
      .finally(() => {
        if (active) setPolicyLoading(false);
      });

    api.paypalStatus()
      .then((nextPayPal) => {
        if (!active) return;
        setPaypal(nextPayPal);
        if (scenario === "paypal") {
          setRail(nextPayPal.configured ? "paypal_sandbox_payouts" : "internal_sandbox");
          setRecipient(nextPayPal.test_recipient_email ?? "");
        }
      })
      .catch((caught) => {
        if (!active) return;
        setPaypal(null);
        setRail("internal_sandbox");
        setPaypalError(caught instanceof Error ? caught.message : "PayPal Sandbox status unavailable");
      })
      .finally(() => {
        if (active) setPaypalLoading(false);
      });

    return () => { active = false; };
  }, [preset, scenario]);

  useEffect(() => {
    if (type !== "payout") setRail("internal_sandbox");
  }, [type]);

  useEffect(() => {
    if (!scenario || !preset && scenario !== "insufficient") return;
    api.startGuidedTest().catch((caught) => {
      setError(caught instanceof Error ? caught.message : "Guided test tracking unavailable");
    });
  }, [preset, scenario]);

  useEffect(() => {
    setConfirming(false);
  }, [amount, category, rail, reason, recipient, type, vendor]);

  useEffect(() => {
    const numeric = Number(amount);
    if (!vendor.trim() || !Number.isFinite(numeric) || numeric <= 0 || !/^\d+(\.\d{1,2})?$/.test(amount) || !category) {
      setPreview(null);
      setPreviewError("");
      setPreviewLoading(false);
      return;
    }
    let active = true;
    setPreviewLoading(true);
    setPreviewError("");
    const timeout = window.setTimeout(() => {
      api.previewPayment({
        vendor: vendor.trim(),
        amount_cents: Math.round(numeric * 100),
        currency: "USD",
        category,
      })
        .then((result) => { if (active) setPreview(result); })
        .catch((caught) => {
          if (!active) return;
          setPreview(null);
          setPreviewError(caught instanceof Error ? caught.message : "Policy preview unavailable");
        })
        .finally(() => { if (active) setPreviewLoading(false); });
    }, 250);
    return () => {
      active = false;
      window.clearTimeout(timeout);
    };
  }, [amount, category, vendor]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    if (!policy) {
      setError("Wait for the active policy to load before creating a request");
      return;
    }
    const numeric = Number(amount);
    if (!Number.isFinite(numeric) || numeric <= 0 || !/^\d+(\.\d{1,2})?$/.test(amount)) {
      setError("Enter a valid amount with no more than two decimal places");
      return;
    }
    const amountCents = Math.round(numeric * 100);
    if (preview?.decision === "approval_required" && !confirming) {
      setConfirming(true);
      return;
    }
    setSubmitting(true);
    const paymentPayload: PaymentPayload = {
      type,
      vendor: vendor.trim(),
      recipient: type === "payout" ? recipient.trim() : null,
      amount_cents: amountCents,
      currency: "USD",
      category,
      reason: reason.trim(),
      rail,
    };
    try {
      const digest = await paymentPayloadDigest(paymentPayload);
      let attempt = paymentAttemptRef.current ?? readPendingPaymentAttempt(attemptKey);
      if (!attempt || attempt.digest !== digest) {
        attempt = { key: createIdempotencyKey("payment"), digest };
        writePendingPaymentAttempt(attemptKey, attempt);
      }
      paymentAttemptRef.current = attempt;
      const result = await api.createPayment(paymentPayload, attempt.key);
      paymentAttemptRef.current = null;
      removePendingPaymentAttempt(attemptKey);
      sessionStorage.removeItem(draftKey);
      navigate(`/app/transactions/${result.transaction.id}`);
    } catch (caught) {
      if (caught instanceof ApiError) {
        const transaction = caught.details?.transaction as { id?: string } | undefined;
        if (transaction?.id) {
          paymentAttemptRef.current = null;
          removePendingPaymentAttempt(attemptKey);
          sessionStorage.removeItem(draftKey);
          navigate(`/app/transactions/${transaction.id}`);
          return;
        }
        setError(caught.message);
      } else {
        setError("Payment request could not be created");
      }
      if (!isAmbiguousMutationError(caught)) {
        paymentAttemptRef.current = null;
        removePendingPaymentAttempt(attemptKey);
      }
    } finally {
      setSubmitting(false);
    }
  }

  const needsConfirmation = preview?.decision === "approval_required";

  async function runInsufficientFundsScenario() {
    const requestKey = guidedInsufficientKeyRef.current ?? createIdempotencyKey("guided-insufficient");
    guidedInsufficientKeyRef.current = requestKey;
    setSubmitting(true);
    setError("");
    try {
      const result = await api.runInsufficientFundsScenario(requestKey);
      guidedInsufficientKeyRef.current = null;
      navigate(`/app/transactions/${result.transaction.id}`);
    } catch (caught) {
      if (!isAmbiguousMutationError(caught)) guidedInsufficientKeyRef.current = null;
      setError(caught instanceof Error ? caught.message : "Insufficient-funds scenario failed");
    } finally {
      setSubmitting(false);
    }
  }

  if (scenario === "insufficient") {
    return <>
      <PageHeader title="Insufficient-funds test" description="Create a real persisted policy outcome without posting a debit" />
      {error ? <div className="mb-5"><ErrorNotice message={error} /></div> : null}
      <Panel className="max-w-2xl p-5 sm:p-6"><h2 className="text-base font-medium">Run the controlled sandbox scenario</h2><p className="mt-3 text-sm leading-6 text-ink-600">Pactra will create temporary auditable policy versions that permit the balance check to run first, submit a request for one cent more than your available sandbox balance, persist the expected block, and restore your prior policy settings. No ledger debit or reservation is created.</p><button className="action-primary mt-6" disabled={submitting} onClick={() => void runInsufficientFundsScenario()} type="button">{submitting ? "Verifying funds control" : "Run insufficient-funds test"}</button></Panel>
    </>;
  }

  return <>
    <PageHeader title="New payment" description="Policy and wallet checks run on the server before any sandbox funds move" />
    {error ? <div className="mb-5"><ErrorNotice message={error} /></div> : null}
    {paypalError ? <div className="mb-5"><ErrorNotice message={`${paypalError}. Internal sandbox payments remain available.`} /></div> : null}
    <div className="grid gap-6 xl:grid-cols-[1fr_360px]">
      <Panel className="p-5 sm:p-6">
        <form className="space-y-6" onSubmit={submit}>
          <fieldset>
            <legend className="text-sm font-medium">Request type</legend>
            <div className="mt-3 grid grid-cols-3 gap-2">
              {(["vendor_payment", "payout", "sandbox_transfer"] as TransactionType[]).map((value) => <button aria-pressed={type === value} className={`h-10 rounded-lg border text-xs font-medium transition-colors ${type === value ? "border-pactra-600 bg-pactra-100 text-pactra-300" : "border-line bg-surface text-ink-600 hover:bg-surface-raised"}`} key={value} onClick={() => setType(value)} type="button">{value === "vendor_payment" ? "Vendor" : value === "payout" ? "Payout" : "Transfer"}</button>)}
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
          <button className="action-primary h-11" disabled={submitting || policyLoading || !policy} type="submit">{policyLoading ? "Loading policy" : submitting ? "Applying policy" : confirming ? "Confirm and create request" : needsConfirmation ? "Review request" : "Create payment request"}</button>
        </form>
      </Panel>
      <aside className="space-y-4">
        <Panel className="p-5" aria-live="polite"><div className="flex items-center gap-2 text-sm font-medium"><ShieldCheck className="h-4 w-4 text-pactra-700" />Likely policy decision</div>{previewLoading ? <p className="mt-4 text-xs text-ink-500">Checking current policy and available funds…</p> : previewError ? <p className="mt-4 text-xs text-negative">{previewError}. Final submission remains server-authoritative.</p> : preview ? <div className="mt-4"><p className={`text-sm font-medium ${preview.decision === "blocked" ? "text-negative" : preview.decision === "approval_required" ? "text-warning-dark" : "text-positive-dark"}`}>{preview.decision === "blocked" ? "Likely blocked" : preview.decision === "approval_required" ? "Likely needs approval" : "Likely auto-approved"}</p><p className="mt-2 text-xs leading-5 text-ink-500">Policy v{preview.policy_version}{preview.reason_code ? ` · ${preview.reason_code.replace(/_/g, " ")}` : " · all checks pass"}. The final decision is recalculated when you submit.</p></div> : <p className="mt-4 text-xs text-ink-500">Enter a vendor and valid amount to preview the current decision.</p>}</Panel>
        <Panel className="p-5"><div className="flex items-center gap-2 text-sm font-medium"><ShieldCheck className="h-4 w-4 text-pactra-700" />Decision order</div><ol className="policy-trace mt-5 space-y-4 text-xs text-ink-600">{["Account and category", "Vendor and payment cap", "Daily and category budgets", "Available wallet funds", "Approval threshold"].map((item, index) => <li className="flex items-center gap-3" key={item}><span>{index + 1}</span>{item}</li>)}</ol></Panel>
        <Panel className="p-5"><p className="text-sm font-medium">Rail disclosure</p><p className="mt-2 text-xs leading-5 text-ink-500">Internal payments use Pactra's simulated ledger. PayPal Sandbox payouts are sent by the configured sandbox business account. The balances are not linked.</p><p aria-live="polite" className={`mt-4 text-xs font-medium ${paypal?.configured ? "text-positive-dark" : "text-ink-500"}`}>{paypalLoading ? "Checking PayPal Sandbox status" : paypalError ? "PayPal status could not be verified; internal sandbox only" : paypal?.configured ? "PayPal Sandbox configured" : "PayPal Sandbox unavailable"}</p><Link className="mt-3 inline-flex text-xs font-medium text-ink-700 underline decoration-line underline-offset-4" to="/app/settings/integrations/paypal">Integration details</Link></Panel>
      </aside>
    </div>
  </>;
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return <label className="block text-sm font-medium text-ink-800">{label}<div className="mt-2">{children}</div></label>;
}

export function AssistantPage() {
  return <AssistantWorkspace />;
}
