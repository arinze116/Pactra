import { Link } from "react-router-dom";
import { useAuth } from "../auth";

type PublicAuthActionsLayout = "desktop" | "mobile" | "legal";

interface PublicAuthActionsProps {
  layout: PublicAuthActionsLayout;
  onNavigate?: () => void;
}

export function PublicAuthActions({ layout, onNavigate }: PublicAuthActionsProps) {
  const { retrySession, status } = useAuth();
  const containerClassName = getContainerClassName(layout);

  if (status === "loading") {
    return (
      <div className={containerClassName} data-auth-state="loading">
        <div className={getStatusClassName(layout)} role="status">
          <span aria-hidden="true" className="h-2 w-2 shrink-0 rounded-full bg-pactra-600" />
          <span>Checking session</span>
        </div>
      </div>
    );
  }

  if (status === "error") {
    return (
      <div className={containerClassName} data-auth-state="error">
        <button className={getSingleActionClassName(layout, "secondary")} onClick={() => void retrySession()} type="button">
          Retry session
        </button>
      </div>
    );
  }

  if (status === "authenticated") {
    return (
      <div className={containerClassName} data-auth-state="authenticated">
        <Link className={getSingleActionClassName(layout, "primary")} onClick={onNavigate} to="/app">Dashboard</Link>
      </div>
    );
  }

  return (
    <div className={containerClassName} data-auth-state="unauthenticated">
      <Link className={getGuestSignInClassName(layout)} onClick={onNavigate} to="/sign-in">Sign in</Link>
      <Link className={getGuestSignUpClassName(layout)} onClick={onNavigate} to="/sign-up">Sign up</Link>
    </div>
  );
}

function getContainerClassName(layout: PublicAuthActionsLayout) {
  if (layout === "mobile") return "mt-4 grid min-h-11 grid-cols-2 gap-2";
  if (layout === "legal") return "flex min-h-11 items-center justify-end gap-2 sm:min-w-[190px] sm:gap-4";
  return "flex min-h-11 min-w-[206px] items-center justify-end gap-4";
}

function getStatusClassName(layout: PublicAuthActionsLayout) {
  const width = layout === "mobile" ? "col-span-2 w-full justify-center" : "justify-end";
  return `flex h-11 items-center gap-2 text-sm text-ink-500 ${width}`;
}

function getSingleActionClassName(layout: PublicAuthActionsLayout, kind: "primary" | "secondary") {
  const base = kind === "primary" ? "action-primary" : "action-secondary";
  return layout === "mobile" ? `${base} col-span-2 w-full` : base;
}

function getGuestSignInClassName(layout: PublicAuthActionsLayout) {
  if (layout === "mobile") return "action-secondary";
  return "inline-flex min-h-11 items-center px-1 text-ink-600 transition-colors duration-150 hover:text-ink-950";
}

function getGuestSignUpClassName(layout: PublicAuthActionsLayout) {
  if (layout === "legal") return "action-primary hidden sm:inline-flex";
  return "action-primary";
}
