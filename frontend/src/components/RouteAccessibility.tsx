import { useEffect, useRef, useState } from "react";
import { useLocation } from "react-router-dom";

function routeTitle(pathname: string): string {
  if (pathname === "/") return "Policy-Controlled Payment Operations";
  if (pathname === "/sign-in") return "Sign in";
  if (pathname === "/sign-up") return "Sign up";
  if (pathname === "/privacy") return "Privacy policy";
  if (pathname === "/terms") return "Terms of use";
  if (pathname === "/app") return "Overview";
  if (pathname === "/app/wallet") return "Wallet";
  if (pathname === "/app/policies") return "Policies";
  if (pathname === "/app/payments/new") return "New payment";
  if (pathname === "/app/assistant" || pathname.startsWith("/app/assistant/")) return "Payment assistant";
  if (pathname === "/app/approvals") return "Approvals";
  if (pathname === "/app/transactions") return "Transactions";
  if (pathname.startsWith("/app/transactions/")) return "Payment receipt";
  if (pathname === "/app/settings") return "Settings";
  if (pathname === "/app/settings/integrations/paypal") return "PayPal Sandbox integration";
  return "Page not found";
}

export function RouteAccessibility() {
  const location = useLocation();
  const previousPath = useRef<string>();
  const [announcement, setAnnouncement] = useState("");

  useEffect(() => {
    const title = routeTitle(location.pathname);
    document.title = `${title} | Pactra`;
    setAnnouncement(`${title} page loaded`);

    const shouldMoveFocus = previousPath.current !== undefined
      && previousPath.current !== location.pathname;
    previousPath.current = location.pathname;
    if (!shouldMoveFocus) return;

    const animationFrame = window.requestAnimationFrame(() => {
      const heading = document.querySelector<HTMLElement>("main h1");
      if (!heading) return;
      const hadTabIndex = heading.hasAttribute("tabindex");
      if (!hadTabIndex) heading.tabIndex = -1;
      heading.focus({ preventScroll: true });
      if (!hadTabIndex) {
        heading.addEventListener("blur", () => heading.removeAttribute("tabindex"), { once: true });
      }
    });
    return () => window.cancelAnimationFrame(animationFrame);
  }, [location.pathname]);

  return <span aria-atomic="true" aria-live="polite" className="sr-only" role="status">{announcement}</span>;
}
