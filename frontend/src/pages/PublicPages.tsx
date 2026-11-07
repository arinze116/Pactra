import { FormEvent, useRef, useState } from "react";
import { ArrowRight, Bot, Check, ChevronDown, CircleDollarSign, Eye, EyeOff, FileCheck2, Menu, ReceiptText, SlidersHorizontal, X } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { ApiError } from "../api";
import { useAuth } from "../auth";
import { BrandMark } from "../components/Brand";
import { ErrorNotice } from "../components/UI";

const productFeatures = [
  { label: "Policy controls", detail: "Set caps, category budgets, vendor blocks, and approval thresholds before execution", icon: SlidersHorizontal },
  { label: "Human approvals", detail: "Route requests above your threshold to a reviewer with the full decision context", icon: FileCheck2 },
  { label: "Payment assistant", detail: "Create governed requests and inspect policy, balances, and receipts through conversation", icon: Bot },
  { label: "Immutable receipts", detail: "Trace each request through policy checks, execution attempts, lifecycle events, and ledger impact", icon: ReceiptText },
];

export function LandingPage() {
  const [featureOpen, setFeatureOpen] = useState(false);
  const [activeFeature, setActiveFeature] = useState(0);
  const [mobileOpen, setMobileOpen] = useState(false);
  const ActiveFeatureIcon = productFeatures[activeFeature].icon;

  return <div className="min-h-screen bg-canvas text-ink-950">
    <header className="relative z-30 border-b border-white/[0.06] bg-canvas/95 backdrop-blur">
      <div className="mx-auto flex h-[72px] max-w-[1500px] items-center justify-between px-5 sm:px-8">
        <Link className="flex items-center gap-3 text-lg font-medium" to="/"><BrandMark />Pactra</Link>
        <nav aria-label="Public navigation" className="hidden items-center gap-7 text-sm md:flex">
          <div className="relative" onMouseEnter={() => setFeatureOpen(true)} onMouseLeave={() => setFeatureOpen(false)}>
            <button aria-expanded={featureOpen} className="flex h-10 items-center gap-1.5 text-ink-600 transition-colors duration-150 hover:text-ink-950" onClick={() => setFeatureOpen((open) => !open)} type="button">Product <ChevronDown className={`h-3.5 w-3.5 transition-transform duration-150 ${featureOpen ? "rotate-180" : ""}`} /></button>
            {featureOpen ? <div className="feature-menu absolute right-0 top-full grid w-[600px] grid-cols-[220px_1fr] overflow-hidden rounded-2xl border border-line bg-surface shadow-float" onFocus={() => setFeatureOpen(true)}>
              <div className="border-r border-line bg-canvas-deep p-2">{productFeatures.map((feature, index) => <button className={`flex w-full items-center gap-3 rounded-lg px-3 py-3 text-left text-sm transition-colors duration-150 ${activeFeature === index ? "bg-surface-raised text-ink-950" : "text-ink-500 hover:bg-surface hover:text-ink-800"}`} key={feature.label} onFocus={() => setActiveFeature(index)} onMouseEnter={() => setActiveFeature(index)} type="button"><feature.icon className="h-4 w-4" strokeWidth={1.5} />{feature.label}</button>)}</div>
              <div className="flex min-h-60 flex-col justify-between p-6"><div><span className="grid h-9 w-9 place-items-center rounded-lg border border-line bg-surface-raised text-pactra-300"><ActiveFeatureIcon className="h-4 w-4" strokeWidth={1.5} /></span><p className="mt-5 text-lg font-medium text-ink-950">{productFeatures[activeFeature].label}</p><p className="mt-2 max-w-sm text-sm leading-6 text-ink-500">{productFeatures[activeFeature].detail}</p></div><Link className="mt-6 inline-flex items-center gap-2 text-sm font-medium text-pactra-300" to="/sign-up">Try it in the sandbox <ArrowRight className="h-4 w-4" /></Link></div>
            </div> : null}
          </div>
          <Link className="text-ink-600 transition-colors duration-150 hover:text-ink-950" to="/sign-in">Sign in</Link>
          <Link className="action-primary" to="/sign-up">Create sandbox</Link>
        </nav>
        <button aria-expanded={mobileOpen} aria-label={mobileOpen ? "Close navigation" : "Open navigation"} className="icon-button md:hidden" onClick={() => setMobileOpen((open) => !open)} type="button">{mobileOpen ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}</button>
      </div>
      {mobileOpen ? <div className="mobile-nav-panel border-t border-line bg-canvas-deep px-5 py-5 md:hidden"><p className="text-xs text-ink-400">Product</p><div className="mt-3 grid gap-2 sm:grid-cols-2">{productFeatures.map((feature) => <div className="rounded-xl border border-line bg-surface p-4" key={feature.label}><feature.icon className="h-4 w-4 text-pactra-300" strokeWidth={1.5} /><p className="mt-3 text-sm font-medium">{feature.label}</p><p className="mt-1 text-xs leading-5 text-ink-500">{feature.detail}</p></div>)}</div><div className="mt-4 grid grid-cols-2 gap-2"><Link className="action-secondary" onClick={() => setMobileOpen(false)} to="/sign-in">Sign in</Link><Link className="action-primary" onClick={() => setMobileOpen(false)} to="/sign-up">Create sandbox</Link></div></div> : null}
    </header>
    <main>
      <section className="relative mx-auto grid min-h-[calc(100vh-72px)] max-w-[1500px] items-center overflow-hidden px-5 py-16 sm:px-8 lg:grid-cols-[1.03fr_0.97fr] lg:gap-14 lg:py-24">
        <div className="pointer-events-none absolute inset-y-0 left-[38%] hidden w-px bg-white/[0.04] lg:block" />
        <div className="hero-copy relative z-10 max-w-4xl"><div className="flex items-center gap-3 text-xs text-ink-500"><span className="h-px w-8 bg-pactra-600" />Governed payment operations</div><h1 className="mt-7 max-w-[900px] text-[clamp(3.25rem,7.4vw,7.5rem)] font-medium leading-[0.9] tracking-[-0.055em] text-white">Control the spend.<br /><span className="text-pactra-600">Prove every move.</span></h1><p className="mt-8 max-w-xl text-base leading-7 text-ink-600 sm:text-lg sm:leading-8">Set policy before a request reaches the ledger. Pactra gives teams enforceable limits, human approvals, immutable receipts, and an honest sandbox payout path.</p><div className="mt-9 flex flex-wrap gap-3"><Link className="action-primary h-12 px-5" to="/sign-up">Open a sandbox <ArrowRight className="h-4 w-4" /></Link><Link className="action-secondary h-12 px-5" to="/sign-in">Sign in</Link></div><div className="mt-10 flex flex-wrap gap-x-8 gap-y-3 border-t border-white/[0.06] pt-5 text-xs text-ink-400"><span>Test funds only</span><span>Atomic policy checks</span><span>Auditable ledger</span></div></div>
        <div className="hero-preview relative mt-16 lg:mt-0"><div className="relative overflow-hidden rounded-[20px] border border-white/[0.09] bg-canvas-deep p-2 shadow-float"><div className="rounded-[14px] border border-white/[0.07] bg-surface"><div className="flex items-center justify-between border-b border-line px-5 py-4"><div className="flex items-center gap-2 text-xs text-ink-500"><span className="h-2 w-2 rounded-full bg-pactra-600" />Illustrative sandbox preview</div><span className="font-mono text-[11px] text-ink-400">SBX-DEMO</span></div><div className="p-5 sm:p-7"><div className="flex items-end justify-between gap-4"><div><p className="text-xs text-ink-500">Available sandbox balance</p><p className="mt-2 text-4xl font-medium tracking-[-0.04em] tabular-nums">$1,000.00</p></div><span className="verified-label"><Check className="h-3.5 w-3.5" />Policy active</span></div><div className="mt-8 grid gap-3 sm:grid-cols-[0.9fr_1.1fr]"><div className="rounded-xl border border-line bg-surface-raised p-4"><div className="flex items-center justify-between"><p className="text-xs text-ink-400">Request</p><CircleDollarSign className="h-4 w-4 text-pactra-300" /></div><p className="mt-5 text-sm text-ink-700">Ada Contractor</p><p className="mt-1 text-2xl font-medium tabular-nums">$125.00</p><p className="mt-5 inline-flex rounded-md bg-warning-soft px-2.5 py-1 text-[11px] text-warning-dark">Needs approval</p></div><div className="rounded-xl border border-pactra-600/25 bg-pactra-50 p-4"><p className="text-xs text-pactra-300">Policy trace</p><ol className="mt-4 space-y-3 text-xs text-ink-700">{["Category allowed", "Budget available", "Approval threshold reached"].map((item, index) => <li className="flex items-center gap-3" key={item}><span className={`grid h-5 w-5 place-items-center rounded-full ${index === 2 ? "bg-warning-soft text-warning-dark" : "bg-emerald-950 text-positive-dark"}`}>{index === 2 ? index + 1 : <Check className="h-3 w-3" />}</span>{item}</li>)}</ol></div></div><div className="mt-3 flex items-center justify-between rounded-lg border border-line px-4 py-3 text-xs text-ink-400"><span>Funds reserved</span><span className="text-warning-dark">Awaiting reviewer</span></div></div></div></div></div>
      </section>
    </main>
  </div>;
}

function AuthPage({ mode }: { mode: "sign-in" | "sign-up" }) {
  const { signIn, signUp } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [passwordVisible, setPasswordVisible] = useState(false);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const passwordInputRef = useRef<HTMLInputElement>(null);
  const isSignUp = mode === "sign-up";
  const passwordInputId = `${mode}-password`;
  const PasswordIcon = passwordVisible ? EyeOff : Eye;
  function togglePasswordVisibility() {
    const input = passwordInputRef.current;
    const selectionStart = input?.selectionStart ?? password.length;
    const selectionEnd = input?.selectionEnd ?? selectionStart;
    setPasswordVisible((visible) => !visible);
    window.requestAnimationFrame(() => {
      passwordInputRef.current?.focus();
      passwordInputRef.current?.setSelectionRange(selectionStart, selectionEnd);
    });
  }
  async function submit(event: FormEvent) {
    event.preventDefault(); setError(""); setSubmitting(true);
    try { if (isSignUp) await signUp(email, password); else await signIn(email, password); navigate("/app", { replace: true }); }
    catch (caught) { setError(caught instanceof ApiError ? caught.message : "Account access failed"); }
    finally { setSubmitting(false); }
  }
  return <div className="grid min-h-screen bg-canvas lg:grid-cols-[0.88fr_1.12fr]"><div className="flex min-h-screen flex-col px-5 py-6 sm:px-10"><Link className="flex items-center gap-3 text-lg font-medium" to="/"><BrandMark />Pactra</Link><div className="my-auto mx-auto w-full max-w-md py-12"><p className="text-xs text-pactra-300">Secure sandbox access</p><h1 className="mt-4 text-4xl font-medium tracking-[-0.04em]">{isSignUp ? "Create your sandbox" : "Return to control"}</h1><p className="mt-3 text-sm leading-6 text-ink-500">{isSignUp ? "Start with $1,000 in clearly labelled test funds." : "Continue managing your governed payment workspace."}</p>{error ? <div className="mt-5"><ErrorNotice message={error} /></div> : null}<form className="mt-8 space-y-5" onSubmit={submit}><label className="block text-sm font-medium text-ink-800">Email<input autoComplete="email" className="input mt-2" onChange={(event) => setEmail(event.target.value)} required type="email" value={email} /></label><div><label className="block text-sm font-medium text-ink-800" htmlFor={passwordInputId}>Password</label><div className="relative mt-2"><input autoComplete={isSignUp ? "new-password" : "current-password"} className="input pr-12" id={passwordInputId} minLength={12} onChange={(event) => setPassword(event.target.value)} ref={passwordInputRef} required type={passwordVisible ? "text" : "password"} value={password} /><button aria-label={passwordVisible ? "Hide password" : "Show password"} aria-pressed={passwordVisible} className="absolute inset-y-0 right-0 grid min-h-11 min-w-11 place-items-center rounded-r-lg text-ink-500 transition-colors hover:text-ink-950" onClick={togglePasswordVisibility} type="button"><PasswordIcon aria-hidden="true" className="h-4 w-4" /></button></div></div>{isSignUp ? <p className="text-xs leading-5 text-ink-500">Use 12–128 characters and at least three of: uppercase, lowercase, number, symbol.</p> : null}<button className="action-primary h-11 w-full" disabled={submitting} type="submit">{submitting ? "Please wait" : isSignUp ? "Create sandbox account" : "Sign in"}</button></form><p className="mt-6 text-sm text-ink-500">{isSignUp ? "Already have an account?" : "New to Pactra?"} <Link className="font-medium text-pactra-300 hover:text-white" to={isSignUp ? "/sign-in" : "/sign-up"}>{isSignUp ? "Sign in" : "Create a sandbox"}</Link></p></div></div><aside className="relative hidden overflow-hidden border-l border-line bg-canvas-deep p-12 lg:flex lg:flex-col lg:justify-between"><p className="text-xs text-ink-400">Pactra / controlled payment operations</p><div className="my-auto max-w-2xl"><div className="grid grid-cols-4 overflow-hidden rounded-2xl border border-line bg-surface">{["Request", "Policy", "Approval", "Ledger"].map((item, index) => <div className={`p-4 ${index ? "border-l border-line" : ""}`} key={item}><p className="font-mono text-xs text-ink-400">0{index + 1}</p><p className="mt-8 text-sm font-medium text-ink-800">{item}</p></div>)}</div><div className="mt-10 border-l-2 border-pactra-600 pl-7"><p className="max-w-xl text-5xl font-medium leading-[1.02] tracking-[-0.05em] text-white">Every request leaves proof.</p><p className="mt-6 max-w-lg text-base leading-7 text-ink-500">Internal payments are simulated in Pactra’s ledger. PayPal Sandbox payouts use the configured sandbox business account. Neither path moves real money.</p></div></div></aside></div>;
}

export const SignInPage = () => <AuthPage mode="sign-in" />;
export const SignUpPage = () => <AuthPage mode="sign-up" />;

export function NotFoundPage({ authenticated = false }: { authenticated?: boolean }) {
  return <div className={authenticated ? "grid min-h-[60vh] place-items-center text-center" : "grid min-h-screen place-items-center bg-canvas px-5 text-center"}><div><p className="text-sm font-medium text-pactra-300">404</p><h1 className="mt-3 text-3xl font-medium">This page does not exist</h1><p className="mt-2 text-sm text-ink-500">Return to a known part of the Pactra sandbox.</p><Link className="action-primary mt-6" to={authenticated ? "/app" : "/"}>{authenticated ? "Go to overview" : "Go home"}</Link></div></div>;
}
