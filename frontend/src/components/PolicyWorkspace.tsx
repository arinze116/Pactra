import { CheckCircle2, Clock3, RotateCcw, ShieldCheck } from "lucide-react";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { api } from "../api";
import { useAuth } from "../auth";
import { markDemoProgress } from "../demoProgress";
import type { Policy, PolicyVersion } from "../types";
import { ErrorNotice, formatCents, LoadingBlock, PageHeader, Panel } from "./UI";

type LimitField = "daily_limit" | "per_transaction_limit" | "approval_threshold";

interface PolicyFormState {
  daily_limit: string;
  per_transaction_limit: string;
  approval_threshold: string;
  categories: string;
  budgets: Record<string, string>;
  blocked_vendors: string;
}

interface PolicyValidation {
  policy: Policy | null;
  errors: Record<string, string>;
}

function dollars(cents: number) {
  return (cents / 100).toFixed(2);
}

function formFromPolicy(policy: Policy): PolicyFormState {
  return {
    daily_limit: dollars(policy.daily_limit_cents),
    per_transaction_limit: dollars(policy.per_transaction_limit_cents),
    approval_threshold: dollars(policy.approval_threshold_cents),
    categories: policy.allowed_categories.join(", "),
    budgets: Object.fromEntries(
      policy.allowed_categories.map((category) => [category, dollars(policy.category_budgets_cents[category])]),
    ),
    blocked_vendors: policy.blocked_vendors.join(", "),
  };
}

function splitValues(value: string) {
  return value.split(",").map((item) => item.trim()).filter(Boolean);
}

function moneyToCents(value: string, allowZero: boolean) {
  const trimmed = value.trim();
  if (!/^\d+(?:\.\d{1,2})?$/.test(trimmed)) return null;
  const cents = Math.round(Number(trimmed) * 100);
  if (!Number.isSafeInteger(cents) || cents > 100_000_000) return null;
  if (allowZero ? cents < 0 : cents <= 0) return null;
  return cents;
}

function validatePolicy(form: PolicyFormState): PolicyValidation {
  const errors: Record<string, string> = {};
  const daily = moneyToCents(form.daily_limit, false);
  const perTransaction = moneyToCents(form.per_transaction_limit, false);
  const approval = moneyToCents(form.approval_threshold, true);
  if (daily === null) errors.daily_limit = "Enter an amount greater than $0 with at most two decimals";
  if (perTransaction === null) errors.per_transaction_limit = "Enter an amount greater than $0 with at most two decimals";
  if (approval === null) errors.approval_threshold = "Enter $0 or a positive amount with at most two decimals";

  const categories = splitValues(form.categories).map((item) => item.toLowerCase());
  if (!categories.length) errors.categories = "Add at least one allowed category";
  else if (new Set(categories).size !== categories.length) errors.categories = "Category names must be unique";
  else if (categories.some((item) => !/^[a-z][a-z0-9_-]{1,31}$/.test(item))) errors.categories = "Use slugs such as software, cloud_ops, or freelance";

  const budgets: Record<string, number> = {};
  for (const category of categories) {
    const budget = moneyToCents(form.budgets[category] ?? "", false);
    if (budget === null) errors[`budget.${category}`] = "Enter a category budget greater than $0";
    else budgets[category] = budget;
  }

  const blocked = splitValues(form.blocked_vendors);
  if (blocked.some((item) => item.length > 100)) errors.blocked_vendors = "Vendor names must be 100 characters or fewer";
  else if (new Set(blocked.map((item) => item.toLowerCase())).size !== blocked.length) errors.blocked_vendors = "Blocked vendors must be unique";

  if (Object.keys(errors).length || daily === null || perTransaction === null || approval === null) {
    return { policy: null, errors };
  }
  return {
    policy: {
      daily_limit_cents: daily,
      per_transaction_limit_cents: perTransaction,
      approval_threshold_cents: approval,
      allowed_categories: categories,
      category_budgets_cents: budgets,
      blocked_vendors: blocked,
      currency: "USD",
    },
    errors,
  };
}

function policiesEqual(left: Policy, right: Policy) {
  return left.daily_limit_cents === right.daily_limit_cents
    && left.per_transaction_limit_cents === right.per_transaction_limit_cents
    && left.approval_threshold_cents === right.approval_threshold_cents
    && left.currency === right.currency
    && left.allowed_categories.length === right.allowed_categories.length
    && left.allowed_categories.every((category, index) => category === right.allowed_categories[index])
    && left.allowed_categories.every((category) => left.category_budgets_cents[category] === right.category_budgets_cents[category])
    && left.blocked_vendors.length === right.blocked_vendors.length
    && left.blocked_vendors.every((vendor, index) => vendor === right.blocked_vendors[index]);
}

export function PolicyWorkspace() {
  const { user } = useAuth();
  const [versions, setVersions] = useState<PolicyVersion[]>([]);
  const [form, setForm] = useState<PolicyFormState | null>(null);
  const [baseline, setBaseline] = useState<Policy | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [current, history] = await Promise.all([api.policy(), api.policyHistory()]);
      setBaseline(current.policy);
      setForm(formFromPolicy(current.policy));
      setVersions(history.items);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Policy could not be loaded");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);
  useEffect(() => {
    if (user?.is_demo && baseline) markDemoProgress("policies_reviewed");
  }, [baseline, user?.is_demo]);

  const validation = useMemo(() => form ? validatePolicy(form) : { policy: null, errors: {} }, [form]);
  const dirty = Boolean(validation.policy && baseline && !policiesEqual(validation.policy, baseline));
  const canSave = Boolean(validation.policy && dirty && !saving);
  const renderedCategories = useMemo(() => {
    if (!form) return [];
    return [...new Set(splitValues(form.categories).map((item) => item.toLowerCase()).filter((item) => /^[a-z][a-z0-9_-]{1,31}$/.test(item)))];
  }, [form]);

  function updateLimit(field: LimitField, value: string) {
    setSuccess("");
    setForm((current) => current ? { ...current, [field]: value } : current);
  }

  function updateCategories(value: string) {
    setSuccess("");
    setForm((current) => {
      if (!current) return current;
      const categories = [...new Set(splitValues(value).map((item) => item.toLowerCase()).filter((item) => /^[a-z][a-z0-9_-]{1,31}$/.test(item)))];
      const budgets = { ...current.budgets };
      for (const category of categories) budgets[category] ??= "100.00";
      return { ...current, categories: value, budgets };
    });
  }

  async function save(event: FormEvent) {
    event.preventDefault();
    setSuccess("");
    setError("");
    if (!form || !validation.policy) {
      setError("Review the highlighted fields before saving this policy");
      return;
    }
    if (!dirty) {
      setError("Change at least one policy field before saving");
      return;
    }
    setSaving(true);
    try {
      const saved = await api.savePolicy(validation.policy);
      const savedForm = formFromPolicy(saved.policy);
      setBaseline(saved.policy);
      setForm(savedForm);
      setSuccess(`Policy version ${saved.version} saved`);
      try {
        const history = await api.policyHistory();
        setVersions(history.items);
      } catch {
        setError("Policy saved, but version history could not refresh. Reload to see the latest immutable version.");
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Policy could not be saved");
    } finally {
      setSaving(false);
    }
  }

  async function reset() {
    if (!window.confirm("Reset the current policy to Pactra defaults?")) return;
    setSaving(true);
    setError("");
    setSuccess("");
    try {
      const saved = await api.resetPolicy();
      setBaseline(saved.policy);
      setForm(formFromPolicy(saved.policy));
      setSuccess(`Policy version ${saved.version} restored to defaults`);
      try {
        const history = await api.policyHistory();
        setVersions(history.items);
      } catch {
        setError("Policy defaults were restored, but version history could not refresh. Reload to see the latest immutable version.");
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Policy reset failed");
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <><PageHeader title="Spending policy" description="Loading the current policy and immutable versions" /><div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_320px]"><LoadingBlock className="h-[520px]" /><LoadingBlock className="h-80" /></div></>;
  if (!form || !baseline) return <><PageHeader title="Spending policy" /><ErrorNotice message={error || "Policy is unavailable"} onRetry={() => void load()} /></>;

  return <>
    <PageHeader title="Spending policy" description="Edit the active controls. Every confirmed save creates a new immutable version." action={<button className="action-secondary" disabled={saving} onClick={() => void reset()} type="button"><RotateCcw className="h-4 w-4" />Reset defaults</button>} />
    {error ? <div className="mb-5"><ErrorNotice message={error} /></div> : null}
    {success ? <div aria-live="polite" className="success-notice mb-5" role="status"><CheckCircle2 aria-hidden="true" className="h-4 w-4" />{success}</div> : null}
    <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_320px]">
      <form className="space-y-5" noValidate onSubmit={save}>
        <Panel className="p-5 sm:p-6">
          <div className="flex items-start gap-3"><span className="policy-section-mark"><ShieldCheck className="h-4 w-4" /></span><div><h2 className="text-base font-medium text-ink-950">Core limits</h2><p className="mt-1 text-sm text-ink-500">Hard caps are evaluated before budget and approval rules</p></div></div>
          <div className="mt-6 grid gap-5 sm:grid-cols-3">
            <MoneyField error={validation.errors.daily_limit} label="Daily limit" onChange={(value) => updateLimit("daily_limit", value)} value={form.daily_limit} />
            <MoneyField error={validation.errors.per_transaction_limit} label="Per transaction" onChange={(value) => updateLimit("per_transaction_limit", value)} value={form.per_transaction_limit} />
            <MoneyField allowZero error={validation.errors.approval_threshold} label="Approval above" onChange={(value) => updateLimit("approval_threshold", value)} value={form.approval_threshold} />
          </div>
        </Panel>

        <Panel className="p-5 sm:p-6">
          <h2 className="text-base font-medium text-ink-950">Categories and budgets</h2>
          <p className="mt-1 text-sm text-ink-500">Each allowed category requires one positive daily budget</p>
          <label className="mt-6 block text-sm font-medium text-ink-700" htmlFor="policy-categories">Allowed categories</label>
          <input aria-describedby="policy-categories-help policy-categories-error" aria-invalid={Boolean(validation.errors.categories)} className="input mt-2" id="policy-categories" onChange={(event) => updateCategories(event.target.value)} value={form.categories} />
          <p className="mt-2 text-xs text-ink-500" id="policy-categories-help">Comma-separated slugs such as software, cloud_ops, freelance</p>
          {validation.errors.categories ? <FieldError id="policy-categories-error">{validation.errors.categories}</FieldError> : null}
          {renderedCategories.length ? <div className="mt-6 grid gap-5 sm:grid-cols-2 xl:grid-cols-3">{renderedCategories.map((category) => <MoneyField error={validation.errors[`budget.${category}`]} key={category} label={`${category} budget`} onChange={(value) => { setSuccess(""); setForm((current) => current ? { ...current, budgets: { ...current.budgets, [category]: value } } : current); }} value={form.budgets[category] ?? ""} />)}</div> : null}
        </Panel>

        <Panel className="p-5 sm:p-6">
          <h2 className="text-base font-medium text-ink-950">Vendor controls</h2>
          <label className="mt-5 block text-sm font-medium text-ink-700" htmlFor="policy-blocked-vendors">Blocked vendors</label>
          <input aria-describedby="policy-blocked-help policy-blocked-error" aria-invalid={Boolean(validation.errors.blocked_vendors)} className="input mt-2" id="policy-blocked-vendors" onChange={(event) => { setSuccess(""); setForm((current) => current ? { ...current, blocked_vendors: event.target.value } : current); }} placeholder="Risky Vendor, Example LLC" value={form.blocked_vendors} />
          <p className="mt-2 text-xs text-ink-500" id="policy-blocked-help">Optional, comma-separated, matched without case sensitivity</p>
          {validation.errors.blocked_vendors ? <FieldError id="policy-blocked-error">{validation.errors.blocked_vendors}</FieldError> : null}
        </Panel>

        <div className="policy-save-bar">
          <div><p className="text-sm font-medium text-ink-800">{!validation.policy ? "Policy needs attention" : dirty ? "Unsaved policy changes" : "Current policy is saved"}</p><p className="mt-1 text-xs text-ink-500">{!validation.policy ? "Review the highlighted fields before saving" : "Changes apply to new requests and are rechecked during approval"}</p></div>
          <button className="action-primary min-w-32" disabled={!canSave} type="submit">{saving ? "Saving" : "Save policy"}</button>
        </div>
      </form>

      <aside className="space-y-5">
        <Panel className="overflow-hidden">
          <div className="border-b border-line px-5 py-4"><div className="flex items-center gap-2"><Clock3 className="h-4 w-4 text-pactra-600" /><h2 className="text-sm font-medium text-ink-950">Version history</h2></div><p className="mt-1 text-xs text-ink-500">Immutable policy snapshots</p></div>
          <div className="max-h-[520px] divide-y divide-line overflow-y-auto">{versions.map((version, index) => <div className="px-5 py-4" key={version.id}><div className="flex items-center justify-between gap-3"><p className="text-sm font-medium text-ink-800">Version {version.version}</p>{index === 0 ? <span className="verified-label"><CheckCircle2 className="h-3.5 w-3.5" />Active</span> : null}</div><p className="mt-2 text-xs text-ink-500">{new Date(version.created_at).toLocaleString()}</p><p className="mt-2 text-xs leading-5 text-ink-500">{formatCents(version.policy.daily_limit_cents)} daily · {version.policy.allowed_categories.length} categories</p></div>)}</div>
        </Panel>
      </aside>
    </div>
  </>;
}

function FieldError({ children, id }: { children: string; id: string }) {
  return <p className="mt-2 text-xs text-negative" id={id}>{children}</p>;
}

function MoneyField({ allowZero = false, error, label, onChange, value }: { allowZero?: boolean; error?: string; label: string; onChange: (value: string) => void; value: string }) {
  const id = `policy-${label.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`;
  return <div><label className="block text-sm font-medium capitalize text-ink-700" htmlFor={id}>{label}</label><div className="relative mt-2"><span className="pointer-events-none absolute left-3 top-2.5 text-sm text-ink-400">$</span><input aria-describedby={error ? `${id}-error` : undefined} aria-invalid={Boolean(error)} className="input pl-7 tabular-nums" id={id} inputMode="decimal" min={allowZero ? "0" : "0.01"} onChange={(event) => onChange(event.target.value)} placeholder={allowZero ? "0.00" : "100.00"} value={value} /></div>{error ? <FieldError id={`${id}-error`}>{error}</FieldError> : null}</div>;
}
