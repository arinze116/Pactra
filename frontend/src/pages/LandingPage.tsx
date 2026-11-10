import { useRef, useState } from "react";
import {
  ArrowRight,
  Bot,
  Check,
  ChevronDown,
  CircleDollarSign,
  FileCheck2,
  Menu,
  ReceiptText,
  SlidersHorizontal,
  X,
} from "lucide-react";
import { Link } from "react-router-dom";
import { useAuth } from "../auth";
import { BrandMark } from "../components/Brand";
import { PublicAuthActions } from "../components/PublicAuthActions";
import { PublicFooter } from "../components/PublicFooter";

const productFeatures = [
  {
    label: "Policy controls",
    detail: "Set caps, category budgets, vendor blocks, and approval thresholds before execution",
    icon: SlidersHorizontal,
  },
  {
    label: "Human approvals",
    detail: "Route requests above your threshold to a reviewer with the full decision context",
    icon: FileCheck2,
  },
  {
    label: "Payment assistant",
    detail: "Create governed requests and inspect policy, balances, and receipts through conversation",
    icon: Bot,
  },
  {
    label: "Auditable receipts",
    detail: "Trace each request through policy checks, execution attempts, lifecycle events, and ledger impact",
    icon: ReceiptText,
  },
];

const workflowSteps = [
  ["Request", "Create a manual request or describe it to the assistant."],
  ["Policy", "Pactra evaluates deterministic limits, recipients, budgets, and available funds."],
  ["Decision", "The request completes, waits for human approval, or is blocked with a reason."],
  ["Evidence", "Receipts, audit events, and balanced ledger entries preserve what happened."],
];

export function LandingPage() {
  const { retrySession, status } = useAuth();
  const [featureOpen, setFeatureOpen] = useState(false);
  const [activeFeature, setActiveFeature] = useState(0);
  const [mobileOpen, setMobileOpen] = useState(false);
  const productMenuButtonRef = useRef<HTMLButtonElement>(null);
  const mobileMenuButtonRef = useRef<HTMLButtonElement>(null);
  const ActiveFeatureIcon = productFeatures[activeFeature].icon;

  return (
    <div className="min-h-screen bg-canvas text-ink-950">
      <a
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-pactra-600 focus:px-4 focus:py-2 focus:text-white"
        href="#public-main-content"
      >
        Skip to content
      </a>
      <header
        className="relative z-30 border-b border-white/[0.06] bg-canvas/95 backdrop-blur"
        onKeyDown={(event) => {
          if (event.key !== "Escape" || !mobileOpen) return;
          setMobileOpen(false);
          mobileMenuButtonRef.current?.focus();
        }}
      >
        <div className="mx-auto flex h-[72px] max-w-[1500px] items-center justify-between px-5 sm:px-8">
          <Link className="flex min-h-11 items-center gap-3 text-lg font-medium" to="/">
            <BrandMark />
            Pactra
          </Link>
          <nav aria-label="Public navigation" className="hidden items-center gap-7 text-sm md:flex">
            <div
              className="relative"
              onBlur={(event) => {
                if (!event.currentTarget.contains(event.relatedTarget)) setFeatureOpen(false);
              }}
              onKeyDown={(event) => {
                if (event.key !== "Escape") return;
                setFeatureOpen(false);
                productMenuButtonRef.current?.focus();
              }}
              onMouseEnter={() => setFeatureOpen(true)}
              onMouseLeave={() => setFeatureOpen(false)}
            >
              <button
                aria-controls="product-feature-panel"
                aria-expanded={featureOpen}
                className="flex h-11 items-center gap-1.5 text-ink-600 transition-colors duration-150 hover:text-ink-950"
                onClick={() => setFeatureOpen((open) => !open)}
                ref={productMenuButtonRef}
                type="button"
              >
                Product
                <ChevronDown
                  aria-hidden="true"
                  className={`h-3.5 w-3.5 transition-transform duration-150 ${featureOpen ? "rotate-180" : ""}`}
                />
              </button>
              {featureOpen ? (
                <div
                  className="feature-menu absolute right-0 top-full grid w-[600px] grid-cols-[220px_1fr] overflow-hidden rounded-2xl border border-line bg-surface shadow-float"
                  id="product-feature-panel"
                  onFocus={() => setFeatureOpen(true)}
                >
                  <div className="border-r border-line bg-canvas-deep p-2">
                    {productFeatures.map((feature, index) => (
                      <button
                        className={`flex w-full items-center gap-3 rounded-lg px-3 py-3 text-left text-sm transition-colors duration-150 ${
                          activeFeature === index
                            ? "bg-surface-raised text-ink-950"
                            : "text-ink-500 hover:bg-surface hover:text-ink-800"
                        }`}
                        key={feature.label}
                        onFocus={() => setActiveFeature(index)}
                        onMouseEnter={() => setActiveFeature(index)}
                        type="button"
                      >
                        <feature.icon aria-hidden="true" className="h-4 w-4" strokeWidth={1.5} />
                        {feature.label}
                      </button>
                    ))}
                  </div>
                  <div className="flex min-h-60 flex-col justify-between p-6">
                    <div>
                      <span className="grid h-9 w-9 place-items-center rounded-lg border border-line bg-surface-raised text-pactra-300">
                        <ActiveFeatureIcon aria-hidden="true" className="h-4 w-4" strokeWidth={1.5} />
                      </span>
                      <p className="mt-5 text-lg font-medium text-ink-950">{productFeatures[activeFeature].label}</p>
                      <p className="mt-2 max-w-sm text-sm leading-6 text-ink-500">{productFeatures[activeFeature].detail}</p>
                    </div>
                    {status === "authenticated" ? (
                      <Link className="mt-6 inline-flex items-center gap-2 text-sm font-medium text-pactra-300" to="/app">
                        Open dashboard
                        <ArrowRight aria-hidden="true" className="h-4 w-4" />
                      </Link>
                    ) : status === "unauthenticated" ? (
                      <Link className="mt-6 inline-flex items-center gap-2 text-sm font-medium text-pactra-300" to="/sign-up">
                        Sign up
                        <ArrowRight aria-hidden="true" className="h-4 w-4" />
                      </Link>
                    ) : status === "error" ? (
                      <button className="mt-6 inline-flex min-h-11 items-center text-sm font-medium text-pactra-300" onClick={() => void retrySession()} type="button">Retry session</button>
                    ) : (
                      <span className="mt-6 inline-flex min-h-11 items-center text-sm text-ink-500" role="status">Checking session</span>
                    )}
                  </div>
                </div>
              ) : null}
            </div>
            <a className="inline-flex min-h-11 items-center px-1 text-ink-600 transition-colors duration-150 hover:text-ink-950" href="#how-it-works">
              How it works
            </a>
            <PublicAuthActions layout="desktop" />
          </nav>
          <button
            aria-controls="public-mobile-navigation"
            aria-expanded={mobileOpen}
            aria-label={mobileOpen ? "Close navigation" : "Open navigation"}
            className="icon-button md:hidden"
            onClick={() => setMobileOpen((open) => !open)}
            ref={mobileMenuButtonRef}
            type="button"
          >
            {mobileOpen ? <X aria-hidden="true" className="h-4 w-4" /> : <Menu aria-hidden="true" className="h-4 w-4" />}
          </button>
        </div>
        {mobileOpen ? (
          <div
            className="mobile-nav-panel border-t border-line bg-canvas-deep px-5 py-5 md:hidden"
            id="public-mobile-navigation"
          >
            <p className="text-xs text-ink-400">Product</p>
            <div className="mt-3 grid gap-2 sm:grid-cols-2">
              {productFeatures.map((feature) => (
                <div className="rounded-xl border border-line bg-surface p-4" key={feature.label}>
                  <feature.icon aria-hidden="true" className="h-4 w-4 text-pactra-300" strokeWidth={1.5} />
                  <p className="mt-3 text-sm font-medium">{feature.label}</p>
                  <p className="mt-1 text-xs leading-5 text-ink-500">{feature.detail}</p>
                </div>
              ))}
            </div>
            <PublicAuthActions layout="mobile" onNavigate={() => setMobileOpen(false)} />
          </div>
        ) : null}
      </header>

      <main id="public-main-content" tabIndex={-1}>
        <section className="relative mx-auto grid min-h-[calc(100vh-72px)] max-w-[1500px] items-center overflow-hidden px-5 py-16 sm:px-8 lg:grid-cols-[1.03fr_0.97fr] lg:gap-14 lg:py-24">
          <div className="pointer-events-none absolute inset-y-0 left-[38%] hidden w-px bg-white/[0.04] lg:block" />
          <div className="hero-copy relative z-10 max-w-4xl">
            <div className="flex items-center gap-3 text-xs text-ink-500">
              <span className="h-px w-8 bg-pactra-600" />
              Governed payment operations
            </div>
            <h1 className="mt-7 max-w-[900px] text-[clamp(3.25rem,7.4vw,7.5rem)] font-medium leading-[0.9] tracking-[-0.055em] text-white">
              Control the spend.<br />
              <span className="text-pactra-600">Prove every move.</span>
            </h1>
            <p className="mt-8 max-w-xl text-base leading-7 text-ink-600 sm:text-lg sm:leading-8">
              Set policy before a request reaches the ledger. Pactra gives teams enforceable limits, human approvals,
              auditable receipts, and an honest sandbox payout path.
            </p>
            <div className="mt-9 flex min-h-12 flex-wrap gap-3">
              {status === "authenticated" ? (
                <Link className="action-primary h-12 px-5" to="/app">
                  Open dashboard
                  <ArrowRight aria-hidden="true" className="h-4 w-4" />
                </Link>
              ) : status === "unauthenticated" ? (
                <>
                  <Link className="action-primary h-12 px-5" to="/sign-up">
                    Sign up
                    <ArrowRight aria-hidden="true" className="h-4 w-4" />
                  </Link>
                  <Link className="action-secondary h-12 px-5" to="/sign-in">Sign in</Link>
                </>
              ) : status === "error" ? (
                <button className="action-secondary h-12 px-5" onClick={() => void retrySession()} type="button">Retry session</button>
              ) : (
                <div className="flex h-12 items-center gap-2 text-sm text-ink-500" role="status">
                  <span aria-hidden="true" className="h-2 w-2 rounded-full bg-pactra-600" />
                  Checking session
                </div>
              )}
            </div>
            <div className="mt-10 flex flex-wrap gap-x-8 gap-y-3 border-t border-white/[0.06] pt-5 text-xs text-ink-400">
              <span>Test funds only</span>
              <span>Atomic policy checks</span>
              <span>Auditable ledger</span>
            </div>
          </div>

          <div className="hero-preview relative mt-16 lg:mt-0">
            <div className="relative overflow-hidden rounded-[20px] border border-white/[0.09] bg-canvas-deep p-2 shadow-float">
              <div className="rounded-[14px] border border-white/[0.07] bg-surface">
                <div className="flex items-center justify-between border-b border-line px-5 py-4">
                  <div className="flex items-center gap-2 text-xs text-ink-500">
                    <span className="h-2 w-2 rounded-full bg-pactra-600" />
                    Illustrative sandbox preview
                  </div>
                  <span className="font-mono text-[11px] text-ink-400">SBX-DEMO</span>
                </div>
                <div className="p-5 sm:p-7">
                  <div className="flex items-end justify-between gap-4">
                    <div>
                      <p className="text-xs text-ink-500">Available sandbox balance</p>
                      <p className="mt-2 text-4xl font-medium tracking-[-0.04em] tabular-nums">$1,000.00</p>
                    </div>
                    <span className="verified-label"><Check aria-hidden="true" className="h-3.5 w-3.5" />Policy active</span>
                  </div>
                  <div className="mt-8 grid gap-3 sm:grid-cols-[0.9fr_1.1fr]">
                    <div className="rounded-xl border border-line bg-surface-raised p-4">
                      <div className="flex items-center justify-between">
                        <p className="text-xs text-ink-400">Request</p>
                        <CircleDollarSign aria-hidden="true" className="h-4 w-4 text-pactra-300" />
                      </div>
                      <p className="mt-5 text-sm text-ink-700">Ada Contractor</p>
                      <p className="mt-1 text-2xl font-medium tabular-nums">$125.00</p>
                      <p className="mt-5 inline-flex rounded-md bg-warning-soft px-2.5 py-1 text-[11px] text-warning-dark">Needs approval</p>
                    </div>
                    <div className="rounded-xl border border-pactra-600/25 bg-pactra-50 p-4">
                      <p className="text-xs text-pactra-300">Policy trace</p>
                      <ol className="mt-4 space-y-3 text-xs text-ink-700">
                        {["Category allowed", "Budget available", "Approval threshold reached"].map((item, index) => (
                          <li className="flex items-center gap-3" key={item}>
                            <span className={`grid h-5 w-5 place-items-center rounded-full ${index === 2 ? "bg-warning-soft text-warning-dark" : "bg-emerald-950 text-positive-dark"}`}>
                              {index === 2 ? index + 1 : <Check aria-hidden="true" className="h-3 w-3" />}
                            </span>
                            {item}
                          </li>
                        ))}
                      </ol>
                    </div>
                  </div>
                  <div className="mt-3 flex items-center justify-between rounded-lg border border-line px-4 py-3 text-xs text-ink-400">
                    <span>Funds reserved</span>
                    <span className="text-warning-dark">Awaiting reviewer</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="border-y border-line bg-canvas-deep" id="how-it-works">
          <div className="mx-auto max-w-[1500px] px-5 py-20 sm:px-8 lg:py-24">
            <div className="max-w-2xl">
              <p className="text-xs font-medium uppercase tracking-[0.14em] text-pactra-300">One governed path</p>
              <h2 className="mt-4 text-3xl font-medium tracking-[-0.035em] sm:text-5xl">A request is never the same as a payment.</h2>
              <p className="mt-5 text-base leading-7 text-ink-500">Manual forms and AI-assisted requests enter the same authenticated service. Deterministic controls decide what can happen next.</p>
            </div>
            <ol className="mt-12 grid gap-px overflow-hidden rounded-2xl border border-line bg-line md:grid-cols-2 xl:grid-cols-4">
              {workflowSteps.map(([title, detail], index) => (
                <li className="bg-surface p-6 sm:p-7" key={title}>
                  <p className="font-mono text-xs text-pactra-300">0{index + 1}</p>
                  <h3 className="mt-8 text-lg font-medium">{title}</h3>
                  <p className="mt-3 text-sm leading-6 text-ink-500">{detail}</p>
                </li>
              ))}
            </ol>
          </div>
        </section>

        <section className="mx-auto grid max-w-[1500px] gap-12 px-5 py-20 sm:px-8 lg:grid-cols-[0.9fr_1.1fr] lg:items-center lg:py-24">
          <div>
            <p className="text-xs font-medium uppercase tracking-[0.14em] text-pactra-300">AI with boundaries</p>
            <h2 className="mt-4 text-3xl font-medium tracking-[-0.035em] sm:text-5xl">AI proposes. Pactra decides.</h2>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            {[
              "AI output is validated as untrusted input.",
              "AI cannot approve or execute its own request.",
              "Policy and available funds remain authoritative.",
              "Provider failure never fabricates completion.",
            ].map((statement) => (
              <div className="flex min-h-28 items-start gap-3 rounded-xl border border-line bg-surface p-5" key={statement}>
                <Check aria-hidden="true" className="mt-0.5 h-4 w-4 shrink-0 text-positive-dark" />
                <p className="text-sm leading-6 text-ink-700">{statement}</p>
              </div>
            ))}
          </div>
        </section>
      </main>

      <PublicFooter />
    </div>
  );
}
