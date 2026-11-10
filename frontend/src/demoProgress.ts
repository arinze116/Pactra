export type DemoProgressKey =
  | "wallet_inspected"
  | "policies_reviewed"
  | "policy_decision_observed"
  | "receipt_viewed";

const STORAGE_KEY = "pactra-demo-progress";
const PROGRESS_EVENT = "pactra:demo-progress";

export function readDemoProgress(): Set<DemoProgressKey> {
  try {
    const stored = JSON.parse(sessionStorage.getItem(STORAGE_KEY) ?? "[]") as unknown;
    if (!Array.isArray(stored)) return new Set();
    return new Set(stored.filter(isDemoProgressKey));
  } catch {
    sessionStorage.removeItem(STORAGE_KEY);
    return new Set();
  }
}

export function markDemoProgress(key: DemoProgressKey) {
  const progress = readDemoProgress();
  if (progress.has(key)) return;
  progress.add(key);
  sessionStorage.setItem(STORAGE_KEY, JSON.stringify([...progress]));
  window.dispatchEvent(new Event(PROGRESS_EVENT));
}

export function clearDemoProgress() {
  sessionStorage.removeItem(STORAGE_KEY);
  window.dispatchEvent(new Event(PROGRESS_EVENT));
}

export function onDemoProgressChange(listener: () => void) {
  window.addEventListener(PROGRESS_EVENT, listener);
  return () => window.removeEventListener(PROGRESS_EVENT, listener);
}

function isDemoProgressKey(value: unknown): value is DemoProgressKey {
  return value === "wallet_inspected"
    || value === "policies_reviewed"
    || value === "policy_decision_observed"
    || value === "receipt_viewed";
}
