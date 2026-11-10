import { useEffect, useRef, useState } from "react";
import { api, createIdempotencyKey } from "../api";
import { useAuth } from "../auth";
import { clearDemoProgress } from "../demoProgress";

type DemoAction = "reset" | "exit" | null;

export function DemoBanner() {
  const { exitDemo } = useAuth();
  const dialogRef = useRef<HTMLDialogElement>(null);
  const resetKeyRef = useRef<string | null>(null);
  const [action, setAction] = useState<DemoAction>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog || !action) return;
    if (!dialog.open) dialog.showModal();
    return () => {
      if (dialog.open) dialog.close();
    };
  }, [action]);

  function openAction(nextAction: Exclude<DemoAction, null>) {
    setError("");
    if (nextAction === "reset" && !resetKeyRef.current) {
      resetKeyRef.current = createIdempotencyKey("demo-reset");
    }
    setAction(nextAction);
  }

  function closeDialog() {
    if (busy) return;
    setAction(null);
    setError("");
    resetKeyRef.current = null;
  }

  async function confirmAction() {
    if (!action || busy) return;
    setBusy(true);
    setError("");
    try {
      if (action === "reset") {
        await api.resetDemo(resetKeyRef.current ?? createIdempotencyKey("demo-reset"));
        clearDemoProgress();
        window.location.assign("/app");
        return;
      }
      await exitDemo();
      window.location.assign("/");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The demo action could not be completed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <div className="demo-banner shrink-0 border-b border-line px-4 py-2.5 sm:px-6">
        <div className="mx-auto flex max-w-[1560px] flex-wrap items-center justify-center gap-x-4 gap-y-2 sm:justify-between">
          <p className="text-center text-[11px] font-medium tracking-[0.08em] text-ink-700 sm:text-left" role="status">DEMO WORKSPACE · SANDBOX FUNDS ONLY · NO REAL MONEY MOVES</p>
          <div className="flex items-center gap-2">
            <button className="demo-banner-action" onClick={() => openAction("reset")} type="button">Reset demo</button>
            <button className="demo-banner-action" onClick={() => openAction("exit")} type="button">Exit demo</button>
          </div>
        </div>
      </div>
      <dialog
        aria-describedby="demo-dialog-description"
        aria-labelledby="demo-dialog-title"
        className="w-[min(92vw,420px)] rounded-2xl border border-line bg-surface p-0 text-ink-950 shadow-float backdrop:bg-black/70"
        onCancel={(event) => {
          event.preventDefault();
          closeDialog();
        }}
        ref={dialogRef}
      >
        <div className="p-5 sm:p-6">
          <h2 className="text-lg font-medium" id="demo-dialog-title">{action === "reset" ? "Reset demo workspace?" : "Exit demo mode?"}</h2>
          <p className="mt-2 text-sm leading-6 text-ink-500" id="demo-dialog-description">
            {action === "reset"
              ? "This restores Northstar Studio's original policies, transactions, wallet state, and walkthrough progress."
              : "This ends the temporary demo session and returns to the public website."}
          </p>
          {error ? <p aria-live="assertive" className="mt-4 rounded-xl border border-negative/20 bg-negative-soft p-3 text-sm text-negative" role="alert">{error}</p> : null}
          <div className="mt-6 flex justify-end gap-2">
            <button autoFocus className="action-secondary" disabled={busy} onClick={closeDialog} type="button">Cancel</button>
            <button className="action-primary" disabled={busy} onClick={() => void confirmAction()} type="button">
              {busy ? (action === "reset" ? "Resetting…" : "Exiting…") : (action === "reset" ? "Reset demo" : "Exit demo")}
            </button>
          </div>
        </div>
      </dialog>
    </>
  );
}
