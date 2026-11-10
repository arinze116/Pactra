import { Link } from "react-router-dom";
import { BrandMark } from "../components/Brand";
import { PublicAuthActions } from "../components/PublicAuthActions";
import { PublicFooter } from "../components/PublicFooter";

interface LegalSection {
  title: string;
  paragraphs: string[];
  items?: string[];
}

const privacySections: LegalSection[] = [
  {
    title: "Scope and sandbox boundary",
    paragraphs: [
      "This notice explains how Pactra handles information in its sandbox payment-governance workspace. Pactra does not provide a bank account, custody service, or live-money payment service.",
      "Use fictional recipients and business data. Do not enter real payment credentials, government identifiers, health information, or other sensitive personal information.",
    ],
  },
  {
    title: "Information Pactra processes",
    paragraphs: ["Pactra processes only the information needed to operate, secure, and demonstrate the workspace."],
    items: [
      "Account information, including your email address and a one-way Argon2id password hash. Pactra does not store your plaintext password.",
      "Essential session and CSRF tokens used to keep you signed in and protect account actions.",
      "Sandbox workspace data, such as fictional recipients, payment descriptions, policy settings, approvals, receipts, and ledger records.",
      "Security and operational data, including request identifiers, timestamps, error classifications, audit events, and rate-limit records.",
      "AI prompts, validated tool arguments, and provider metadata when the optional Gemini feature is enabled.",
      "PayPal Sandbox identifiers and item status when an authorised sandbox payout workflow is used.",
    ],
  },
  {
    title: "How information is used",
    paragraphs: ["Information is used to authenticate users, enforce tenant ownership, evaluate spending policy, operate the sandbox ledger, show receipts and audit history, prevent abuse, diagnose failures, and improve demo reliability."],
  },
  {
    title: "Service providers",
    paragraphs: [
      "Depending on the environment, Pactra may use Vercel for the frontend, Oracle Cloud infrastructure for the API and worker, PostgreSQL for storage, Gemini for optional function calling, and PayPal Sandbox for authorised provider demonstrations.",
      "Gemini and PayPal are not contacted merely because you view a public page. Provider features are controlled by server-side configuration and deterministic application rules.",
    ],
  },
  {
    title: "Cookies and local browser storage",
    paragraphs: [
      "Pactra uses essential cookies for the authenticated session and CSRF protection. These cookies are not used for advertising.",
      "The application may use limited browser storage for safe interface recovery, such as preserving an idempotency key after an interrupted request. It does not store your password or provider credentials in browser storage.",
    ],
  },
  {
    title: "Retention and security",
    paragraphs: [
      "Sandbox account, transaction, receipt, and audit records may be retained to preserve the product's accountability model and investigate failures. No self-service account deletion workflow is currently implemented.",
      "Pactra uses password hashing, opaque server-side sessions, CSRF protection, owner-scoped queries, strict request validation, security headers, and database constraints. No internet service can promise absolute security.",
    ],
  },
  {
    title: "Your choices and contact",
    paragraphs: [
      "You can avoid optional AI or PayPal Sandbox workflows and use the internal deterministic sandbox path. You can sign out at any time and change your password from Settings.",
      "For privacy questions, contact the repository owner through the Pactra GitHub project. Do not post passwords, tokens, recipient details, or other sensitive information in a public issue.",
    ],
  },
];

const termsSections: LegalSection[] = [
  {
    title: "Sandbox-only service",
    paragraphs: [
      "Pactra is a demonstration and engineering project for governed payment operations. All in-app wallet funds are simulated. Pactra is not a bank, money transmitter, payment processor, escrow service, or financial adviser.",
      "The optional PayPal integration is restricted to PayPal Sandbox. Do not use Pactra to represent that a real payment has occurred.",
    ],
  },
  {
    title: "Accounts and access",
    paragraphs: [
      "You are responsible for the email address and password used for your account and for activity performed through an active session. Use a unique password and sign out on shared devices.",
      "Do not attempt to access another user's workspace, bypass rate limits, interfere with service operation, or test production destructively.",
    ],
  },
  {
    title: "Governed actions",
    paragraphs: [
      "A submitted request is not proof of completion. Deterministic policy, available sandbox funds, approval state, worker processing, and final provider item status determine the result.",
      "AI output is untrusted input. Gemini cannot approve its own request, bypass policy, directly submit PayPal payouts, or directly change ledger balances.",
    ],
  },
  {
    title: "Acceptable use",
    paragraphs: ["Use Pactra only for lawful sandbox evaluation, development, and demonstrations."],
    items: [
      "Use fictional business and recipient data unless you have a lawful reason and permission to process it.",
      "Do not upload secrets, live payment credentials, malicious content, or personal data that is not needed for a sandbox test.",
      "Do not automate abusive registration, login attempts, provider requests, or duplicate financial operations.",
      "Do not claim a sandbox result is a real payment, regulated service, or third-party certification.",
    ],
  },
  {
    title: "Availability and changes",
    paragraphs: [
      "Pactra may be unavailable, changed, reset, or discontinued. External providers can fail, time out, rate limit requests, or change their sandbox behaviour.",
      "Material changes should follow the project's normal branch, review, testing, and release process. These terms may be updated when product behaviour or legal requirements change.",
    ],
  },
  {
    title: "Open-source licence and warranty",
    paragraphs: [
      "The Pactra source code is provided under the MIT License. The software is provided as-is, without warranties of merchantability, fitness for a particular purpose, or non-infringement, to the extent permitted by law.",
      "Nothing in these terms creates a banking, fiduciary, employment, partnership, or agency relationship.",
    ],
  },
  {
    title: "Contact",
    paragraphs: ["Questions about these terms can be directed to the repository owner through the Pactra GitHub project. Do not include secrets or sensitive account information in public correspondence."],
  },
];

function LegalPage({
  eyebrow,
  title,
  introduction,
  sections,
}: {
  eyebrow: string;
  title: string;
  introduction: string;
  sections: LegalSection[];
}) {
  return (
    <div className="min-h-screen bg-canvas text-ink-950">
      <a
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-pactra-600 focus:px-4 focus:py-2 focus:text-white"
        href="#legal-content"
      >
        Skip to content
      </a>
      <header className="border-b border-line bg-canvas/95 backdrop-blur">
        <div className="mx-auto flex min-h-[72px] max-w-[1200px] items-center justify-between gap-4 px-5 sm:px-8">
          <Link className="inline-flex min-h-11 items-center gap-3 text-lg font-medium" to="/">
            <BrandMark />
            Pactra
          </Link>
          <nav aria-label="Legal page navigation"><PublicAuthActions layout="legal" /></nav>
        </div>
      </header>

      <main className="mx-auto max-w-[1200px] px-5 py-16 sm:px-8 lg:py-24" id="legal-content" tabIndex={-1}>
        <div className="grid gap-12 lg:grid-cols-[280px_1fr] lg:gap-20">
          <aside className="lg:sticky lg:top-10 lg:self-start">
            <p className="text-xs font-medium uppercase tracking-[0.14em] text-pactra-300">{eyebrow}</p>
            <p className="mt-5 text-sm leading-6 text-ink-500">Last updated 9 November 2026</p>
            <nav aria-label={`${title} sections`} className="mt-8 hidden lg:block">
              <ol className="space-y-1 border-l border-line pl-4">
                {sections.map((section, index) => (
                  <li key={section.title}>
                    <a className="inline-flex min-h-9 items-center text-sm text-ink-500 hover:text-ink-950" href={`#section-${index + 1}`}>
                      {section.title}
                    </a>
                  </li>
                ))}
              </ol>
            </nav>
          </aside>

          <article className="min-w-0">
            <h1 className="text-4xl font-medium tracking-[-0.04em] sm:text-6xl">{title}</h1>
            <p className="mt-6 max-w-3xl text-lg leading-8 text-ink-600">{introduction}</p>
            <div className="mt-12 divide-y divide-line border-y border-line">
              {sections.map((section, index) => (
                <section className="scroll-mt-8 py-9" id={`section-${index + 1}`} key={section.title}>
                  <h2 className="text-xl font-medium tracking-[-0.02em]">{index + 1}. {section.title}</h2>
                  <div className="mt-4 space-y-4 text-sm leading-7 text-ink-500">
                    {section.paragraphs.map((paragraph) => <p key={paragraph}>{paragraph}</p>)}
                    {section.items ? (
                      <ul className="list-disc space-y-2 pl-5 marker:text-pactra-300">
                        {section.items.map((item) => <li className="pl-1" key={item}>{item}</li>)}
                      </ul>
                    ) : null}
                  </div>
                </section>
              ))}
            </div>
          </article>
        </div>
      </main>

      <PublicFooter />
    </div>
  );
}

export function PrivacyPage() {
  return (
    <LegalPage
      eyebrow="Privacy"
      introduction="A plain-language account of the information Pactra processes, why it is needed, and the limits of this sandbox product."
      sections={privacySections}
      title="Privacy policy"
    />
  );
}

export function TermsPage() {
  return (
    <LegalPage
      eyebrow="Legal"
      introduction="The rules for using Pactra as a sandbox demonstration of deterministic payment governance."
      sections={termsSections}
      title="Terms of use"
    />
  );
}
