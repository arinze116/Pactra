import { FormEvent, useRef, useState } from "react";
import { Eye, EyeOff } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { ApiError } from "../api";
import { useAuth } from "../auth";
import { BrandMark } from "../components/Brand";
import { PublicFooter } from "../components/PublicFooter";
import { ErrorNotice } from "../components/UI";
import {
  PASSWORD_MAX_LENGTH,
  PASSWORD_MIN_LENGTH,
  PASSWORD_REQUIREMENTS,
} from "../passwordPolicy";

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
  const passwordRequirementsId = `${mode}-password-requirements`;
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
    event.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      if (isSignUp) await signUp(email, password);
      else await signIn(email, password);
      navigate("/app", { replace: true });
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Account access failed. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen flex-col bg-canvas text-ink-950">
      <div className="grid flex-1 lg:grid-cols-[0.88fr_1.12fr]">
        <main className="flex min-h-[720px] flex-col px-5 py-6 sm:px-10">
          <Link className="flex min-h-11 items-center gap-3 text-lg font-medium" to="/">
            <BrandMark />
            Pactra
          </Link>
          <div className="my-auto mx-auto w-full max-w-md py-12">
            <p className="text-xs text-pactra-300">Secure sandbox access</p>
            <h1 className="mt-4 text-4xl font-medium tracking-[-0.04em]">
              {isSignUp ? "Create your sandbox" : "Return to control"}
            </h1>
            <p className="mt-3 text-sm leading-6 text-ink-500">
              {isSignUp
                ? "Start with $1,000 in clearly labelled test funds."
                : "Continue managing your governed payment workspace."}
            </p>
            {error ? <div className="mt-5"><ErrorNotice message={error} /></div> : null}
            <form className="mt-8 space-y-5" onSubmit={submit}>
              <label className="block text-sm font-medium text-ink-800">
                Email
                <input
                  autoCapitalize="none"
                  autoComplete="email"
                  className="input mt-2"
                  disabled={submitting}
                  maxLength={254}
                  onChange={(event) => setEmail(event.target.value)}
                  required
                  spellCheck={false}
                  type="email"
                  value={email}
                />
              </label>
              <div>
                <label className="block text-sm font-medium text-ink-800" htmlFor={passwordInputId}>Password</label>
                <div className="relative mt-2">
                  <input
                    aria-describedby={isSignUp ? passwordRequirementsId : undefined}
                    autoComplete={isSignUp ? "new-password" : "current-password"}
                    className="input pr-12"
                    disabled={submitting}
                    id={passwordInputId}
                    maxLength={PASSWORD_MAX_LENGTH}
                    minLength={isSignUp ? PASSWORD_MIN_LENGTH : undefined}
                    onChange={(event) => setPassword(event.target.value)}
                    ref={passwordInputRef}
                    required
                    type={passwordVisible ? "text" : "password"}
                    value={password}
                  />
                  <button
                    aria-label={passwordVisible ? "Hide password" : "Show password"}
                    aria-pressed={passwordVisible}
                    className="absolute inset-y-0 right-0 grid min-h-11 min-w-11 place-items-center rounded-r-lg text-ink-500 transition-colors hover:text-ink-950 disabled:cursor-not-allowed disabled:opacity-40"
                    disabled={submitting}
                    onClick={togglePasswordVisibility}
                    type="button"
                  >
                    <PasswordIcon aria-hidden="true" className="h-4 w-4" />
                  </button>
                </div>
              </div>
              {isSignUp ? (
                <p className="text-xs leading-5 text-ink-500" id={passwordRequirementsId}>{PASSWORD_REQUIREMENTS}</p>
              ) : null}
              <button className="action-primary h-11 w-full" disabled={submitting} type="submit">
                {submitting ? "Please wait" : isSignUp ? "Create sandbox account" : "Sign in"}
              </button>
            </form>
            {isSignUp ? (
              <p className="mt-4 text-xs leading-5 text-ink-400">
                By creating an account, you agree to the <Link className="text-ink-700 underline decoration-line underline-offset-4 hover:text-white" to="/terms">Terms of use</Link> and acknowledge the <Link className="text-ink-700 underline decoration-line underline-offset-4 hover:text-white" to="/privacy">Privacy policy</Link>.
              </p>
            ) : null}
            <p className="mt-6 text-sm text-ink-500">
              {isSignUp ? "Already have an account?" : "New to Pactra?"}{" "}
              <Link className="font-medium text-pactra-300 hover:text-white" to={isSignUp ? "/sign-in" : "/sign-up"}>
                {isSignUp ? "Sign in" : "Create a sandbox"}
              </Link>
            </p>
          </div>
        </main>

        <aside className="relative hidden overflow-hidden border-l border-line bg-canvas-deep p-12 lg:flex lg:flex-col lg:justify-between">
          <p className="text-xs text-ink-400">Pactra / controlled payment operations</p>
          <div className="my-auto max-w-2xl">
            <div className="grid grid-cols-4 overflow-hidden rounded-2xl border border-line bg-surface">
              {["Request", "Policy", "Approval", "Ledger"].map((item, index) => (
                <div className={`p-4 ${index ? "border-l border-line" : ""}`} key={item}>
                  <p className="font-mono text-xs text-ink-400">0{index + 1}</p>
                  <p className="mt-8 text-sm font-medium text-ink-800">{item}</p>
                </div>
              ))}
            </div>
            <div className="mt-10 border-l-2 border-pactra-600 pl-7">
              <p className="max-w-xl text-5xl font-medium leading-[1.02] tracking-[-0.05em] text-white">Every request leaves proof.</p>
              <p className="mt-6 max-w-lg text-base leading-7 text-ink-500">
                Internal payments are simulated in Pactra's ledger. PayPal Sandbox payouts use the configured sandbox
                business account. Neither path moves real money.
              </p>
            </div>
          </div>
        </aside>
      </div>

      <PublicFooter />
    </div>
  );
}

export const SignInPage = () => <AuthPage mode="sign-in" />;
export const SignUpPage = () => <AuthPage mode="sign-up" />;
