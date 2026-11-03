import { FormEvent, useState } from "react";
import { ArrowRight, Check, ShieldCheck } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { ApiError } from "../api";
import { useAuth } from "../auth";
import { ErrorNotice } from "../components/UI";

export function LandingPage() {
  return <div className="min-h-screen bg-[#f7f4ee] text-ink-950">
    <header className="mx-auto flex h-16 max-w-[1440px] items-center justify-between px-5 sm:px-8"><Link className="flex items-center gap-2 text-lg font-medium" to="/"><ShieldCheck className="h-5 w-5 text-pactra-700" strokeWidth={1.5} />Pactra</Link><nav className="flex items-center gap-5 text-sm"><Link className="text-ink-600 hover:text-ink-950" to="/sign-in">Sign in</Link><Link className="rounded-lg bg-ink-950 px-4 py-2.5 font-medium text-white" to="/sign-up">Create sandbox account</Link></nav></header>
    <main className="mx-auto grid min-h-[calc(100vh-64px)] max-w-[1440px] items-center gap-12 px-5 py-16 sm:px-8 lg:grid-cols-[0.8fr_1.2fr] lg:py-20">
      <div className="max-w-xl"><p className="text-sm font-medium text-pactra-700">Governed sandbox payments</p><h1 className="mt-5 text-5xl font-medium leading-[1.04] tracking-[-0.035em] sm:text-6xl">Set the rules before funds move</h1><p className="mt-6 max-w-lg text-lg leading-8 text-ink-600">Pactra gives small teams a test wallet, enforceable spending policies, human approvals, and an auditable PayPal Sandbox payout path.</p><div className="mt-8 flex flex-wrap gap-3"><Link className="inline-flex h-12 items-center gap-2 rounded-lg bg-ink-950 px-5 text-sm font-medium text-white" to="/sign-up">Open a sandbox <ArrowRight className="h-4 w-4" /></Link><Link className="inline-flex h-12 items-center rounded-lg border border-ink-300 bg-white/60 px-5 text-sm font-medium text-ink-800" to="/sign-in">Sign in</Link></div><p className="mt-5 text-xs text-ink-500">Test funds only. PayPal execution uses Sandbox credentials configured by the operator.</p></div>
      <div className="overflow-hidden rounded-[20px] border border-ink-950/10 bg-[#111612] p-3 shadow-[0_24px_70px_rgba(31,27,22,0.16)]"><div className="rounded-2xl border border-white/10 bg-[#171d18] p-5 text-white sm:p-6"><div className="flex items-center justify-between"><div><p className="text-xs text-white/45">Available sandbox balance</p><p className="mt-2 text-3xl font-medium tabular-nums">$1,000.00</p></div><span className="rounded-md border border-emerald-300/20 bg-emerald-300/10 px-2.5 py-1 text-xs text-emerald-200">Policy active</span></div><div className="mt-8 grid gap-3 sm:grid-cols-2"><div className="rounded-xl border border-white/10 bg-white/[0.04] p-4"><p className="text-xs text-white/45">Request</p><p className="mt-2 text-sm">Ada Contractor</p><p className="mt-1 text-xl tabular-nums">$125.00</p><p className="mt-3 text-xs text-amber-200">Needs approval</p></div><div className="rounded-xl bg-[#eaf6ef] p-4 text-ink-950"><p className="text-xs text-ink-500">Policy trace</p><ol className="mt-3 space-y-3 text-xs">{["Category allowed", "Budget available", "Approval threshold reached"].map((item, index) => <li className="flex items-center gap-3" key={item}><span className={`grid h-5 w-5 place-items-center rounded-full ${index === 2 ? "bg-amber-100 text-amber-800" : "bg-pactra-100 text-pactra-700"}`}>{index === 2 ? index + 1 : <Check className="h-3 w-3" />}</span>{item}</li>)}</ol></div></div></div></div>
    </main>
  </div>;
}

function AuthPage({ mode }: { mode: "sign-in" | "sign-up" }) {
  const { signIn, signUp } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const isSignUp = mode === "sign-up";
  async function submit(event: FormEvent) {
    event.preventDefault(); setError(""); setSubmitting(true);
    try { if (isSignUp) await signUp(email, password); else await signIn(email, password); navigate("/app", { replace: true }); }
    catch (caught) { setError(caught instanceof ApiError ? caught.message : "Account access failed"); }
    finally { setSubmitting(false); }
  }
  return <div className="grid min-h-screen bg-canvas lg:grid-cols-[0.9fr_1.1fr]"><div className="flex min-h-screen flex-col px-5 py-6 sm:px-10"><Link className="flex items-center gap-2 text-lg font-medium" to="/"><ShieldCheck className="h-5 w-5 text-pactra-700" />Pactra</Link><div className="my-auto mx-auto w-full max-w-md py-12"><h1 className="text-3xl font-medium">{isSignUp ? "Create your sandbox" : "Sign in to Pactra"}</h1><p className="mt-2 text-sm leading-6 text-ink-500">{isSignUp ? "Start with $1,000 in clearly labelled test funds." : "Continue managing your sandbox payment controls."}</p>{error ? <div className="mt-5"><ErrorNotice message={error} /></div> : null}<form className="mt-7 space-y-5" onSubmit={submit}><label className="block text-sm font-medium">Email<input autoComplete="email" className="mt-2 h-11 w-full rounded-lg border border-line bg-white px-3 outline-none focus:border-pactra-600" onChange={(event) => setEmail(event.target.value)} required type="email" value={email} /></label><label className="block text-sm font-medium">Password<input autoComplete={isSignUp ? "new-password" : "current-password"} className="mt-2 h-11 w-full rounded-lg border border-line bg-white px-3 outline-none focus:border-pactra-600" minLength={12} onChange={(event) => setPassword(event.target.value)} required type="password" value={password} /></label>{isSignUp ? <p className="text-xs leading-5 text-ink-500">Use 12–128 characters and at least three of: uppercase, lowercase, number, symbol.</p> : null}<button className="h-11 w-full rounded-lg bg-ink-950 text-sm font-medium text-white disabled:opacity-50" disabled={submitting} type="submit">{submitting ? "Please wait" : isSignUp ? "Create sandbox account" : "Sign in"}</button></form><p className="mt-6 text-sm text-ink-500">{isSignUp ? "Already have an account?" : "New to Pactra?"} <Link className="font-medium text-ink-950" to={isSignUp ? "/sign-in" : "/sign-up"}>{isSignUp ? "Sign in" : "Create a sandbox"}</Link></p></div></div><aside className="hidden bg-ink-950 p-12 text-white lg:flex lg:flex-col lg:justify-end"><p className="max-w-xl text-4xl font-medium leading-tight">Every request leaves a policy decision, a ledger trail, and a receipt.</p><p className="mt-5 max-w-lg text-base leading-7 text-white/55">Internal payments are simulated in Pactra’s ledger. PayPal Sandbox payouts use the configured sandbox business account. Neither path moves real money.</p></aside></div>;
}

export const SignInPage = () => <AuthPage mode="sign-in" />;
export const SignUpPage = () => <AuthPage mode="sign-up" />;

export function NotFoundPage({ authenticated = false }: { authenticated?: boolean }) {
  return <div className={authenticated ? "grid min-h-[60vh] place-items-center text-center" : "grid min-h-screen place-items-center bg-canvas px-5 text-center"}><div><p className="text-sm font-medium text-pactra-700">404</p><h1 className="mt-3 text-3xl font-medium">This page does not exist</h1><p className="mt-2 text-sm text-ink-500">Return to a known part of the Pactra sandbox.</p><Link className="mt-6 inline-flex h-10 items-center rounded-lg bg-ink-950 px-4 text-sm font-medium text-white" to={authenticated ? "/app" : "/"}>{authenticated ? "Go to overview" : "Go home"}</Link></div></div>;
}
