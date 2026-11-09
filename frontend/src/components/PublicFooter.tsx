import { ArrowUpRight } from "lucide-react";
import { Link } from "react-router-dom";
import { BrandMark } from "./Brand";

const repositoryUrl = "https://github.com/arinze116/Pactra";

const productLinks = [
  { label: "Overview", to: "/" },
  { label: "Create account", to: "/sign-up" },
  { label: "Sign in", to: "/sign-in" },
];

const resourceLinks = [
  { label: "Project README", href: `${repositoryUrl}#readme` },
  { label: "Demo guide", href: `${repositoryUrl}/tree/main/DEMO` },
  { label: "Source code", href: repositoryUrl },
];

const legalLinks = [
  { kind: "internal", label: "Privacy policy", to: "/privacy" },
  { kind: "internal", label: "Terms of use", to: "/terms" },
  { kind: "external", label: "MIT licence", href: `${repositoryUrl}/blob/main/LICENSE` },
] as const;

function ExternalLink({ href, label }: { href: string; label: string }) {
  return (
    <a
      className="inline-flex min-h-11 items-center gap-1.5 text-sm text-ink-500 transition-colors hover:text-ink-950"
      href={href}
      rel="noreferrer"
      target="_blank"
    >
      {label}
      <span className="sr-only"> (opens in a new tab)</span>
      <ArrowUpRight aria-hidden="true" className="h-3.5 w-3.5" />
    </a>
  );
}

export function PublicFooter() {
  return (
    <footer className="border-t border-line bg-canvas-deep" data-testid="public-footer">
      <div className="mx-auto max-w-[1500px] px-5 py-12 sm:px-8 lg:py-16">
        <div className="grid gap-10 lg:grid-cols-[1.4fr_2fr] lg:gap-16">
          <div className="max-w-md">
            <Link className="inline-flex min-h-11 items-center gap-3 text-lg font-medium" to="/">
              <BrandMark />
              Pactra
            </Link>
            <p className="mt-4 text-sm leading-6 text-ink-500">
              Governed payment operations for small teams. Every request passes through deterministic policy,
              approval, and ledger controls.
            </p>
            <p className="mt-5 inline-flex rounded-full border border-warning/20 bg-warning-soft px-3 py-1.5 text-xs text-warning-dark">
              Sandbox funds only. No real money moves.
            </p>
          </div>

          <nav aria-label="Footer navigation" className="grid gap-8 sm:grid-cols-3">
            <div>
              <h2 className="text-xs font-medium uppercase tracking-[0.14em] text-ink-700">Product</h2>
              <ul className="mt-3 space-y-1">
                {productLinks.map((link) => (
                  <li key={link.to}>
                    <Link className="inline-flex min-h-11 items-center text-sm text-ink-500 transition-colors hover:text-ink-950" to={link.to}>
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>

            <div>
              <h2 className="text-xs font-medium uppercase tracking-[0.14em] text-ink-700">Resources</h2>
              <ul className="mt-3 space-y-1">
                {resourceLinks.map((link) => (
                  <li key={link.href}>
                    <ExternalLink href={link.href} label={link.label} />
                  </li>
                ))}
              </ul>
            </div>

            <div>
              <h2 className="text-xs font-medium uppercase tracking-[0.14em] text-ink-700">Legal</h2>
              <ul className="mt-3 space-y-1">
                {legalLinks.map((link) => (
                  <li key={link.label}>
                    {link.kind === "internal" ? (
                      <Link className="inline-flex min-h-11 items-center text-sm text-ink-500 transition-colors hover:text-ink-950" to={link.to}>
                        {link.label}
                      </Link>
                    ) : (
                      <ExternalLink href={link.href} label={link.label} />
                    )}
                  </li>
                ))}
              </ul>
            </div>
          </nav>
        </div>

        <div className="mt-10 flex flex-col gap-3 border-t border-line pt-6 text-xs text-ink-400 sm:flex-row sm:items-center sm:justify-between">
          <p>Copyright {new Date().getFullYear()} Pactra.</p>
          <p>Built for transparent, governed sandbox payment demonstrations.</p>
        </div>
      </div>
    </footer>
  );
}
