import { Component, lazy, Suspense } from "react";
import type { ErrorInfo, ReactNode } from "react";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { AuthProvider, GuestRoute, ProtectedRoute } from "./auth";
import { AppShell } from "./components/AppShell";
import { OverviewPage } from "./pages/OverviewPage";
import { AssistantPage, NewPaymentPage } from "./pages/PaymentPages";
import { LandingPage, NotFoundPage, SignInPage, SignUpPage } from "./pages/PublicPages";

const ApprovalsPage = lazy(() => import("./pages/TransactionPages").then((module) => ({ default: module.ApprovalsPage })));
const TransactionsPage = lazy(() => import("./pages/TransactionPages").then((module) => ({ default: module.TransactionsPage })));
const ReceiptPage = lazy(() => import("./pages/TransactionPages").then((module) => ({ default: module.ReceiptPage })));
const PoliciesPage = lazy(() => import("./pages/ControlPages").then((module) => ({ default: module.PoliciesPage })));
const WalletPage = lazy(() => import("./pages/ControlPages").then((module) => ({ default: module.WalletPage })));
const SettingsPage = lazy(() => import("./pages/ControlPages").then((module) => ({ default: module.SettingsPage })));
const PayPalIntegrationPage = lazy(() => import("./pages/ControlPages").then((module) => ({ default: module.PayPalIntegrationPage })));

class AppErrorBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  componentDidCatch(error: Error, info: ErrorInfo) { if (import.meta.env.DEV) console.error("Pactra render error", error, info.componentStack); }
  render() {
    if (this.state.failed) return <div className="grid min-h-screen place-items-center bg-canvas p-6 text-center"><div><h1 className="text-2xl font-medium">The workspace could not render</h1><p className="mt-2 text-sm text-ink-500">Reload the page or return to the overview.</p><div className="mt-5 flex justify-center gap-3"><button className="action-secondary" onClick={() => window.location.reload()}>Reload page</button><a className="action-primary" href="/app">Go to overview</a></div></div></div>;
    return this.props.children;
  }
}

function RouteLoader() { return <div className="grid min-h-64 place-items-center text-sm text-ink-500">Loading page</div>; }

export default function PactraApp() {
  return <AppErrorBoundary><BrowserRouter><AuthProvider><Suspense fallback={<RouteLoader />}><Routes>
    <Route path="/" element={<LandingPage />} />
    <Route element={<GuestRoute />}><Route path="/sign-in" element={<SignInPage />} /><Route path="/sign-up" element={<SignUpPage />} /></Route>
    <Route element={<ProtectedRoute />}><Route path="/app" element={<AppShell />}><Route index element={<OverviewPage />} /><Route path="payments/new" element={<NewPaymentPage />} /><Route path="assistant" element={<AssistantPage />} /><Route path="assistant/:conversationId" element={<AssistantPage />} /><Route path="approvals" element={<ApprovalsPage />} /><Route path="transactions" element={<TransactionsPage />} /><Route path="transactions/:id" element={<ReceiptPage />} /><Route path="policies" element={<PoliciesPage />} /><Route path="wallet" element={<WalletPage />} /><Route path="settings" element={<SettingsPage />} /><Route path="settings/integrations/paypal" element={<PayPalIntegrationPage />} /><Route path="*" element={<NotFoundPage authenticated />} /></Route></Route>
    <Route path="*" element={<NotFoundPage />} />
  </Routes></Suspense></AuthProvider></BrowserRouter></AppErrorBoundary>;
}
