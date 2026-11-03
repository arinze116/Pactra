import type { Policy, SpendSummary } from "../types";
import { PolicyOverview } from "./PolicyOverview";

interface PolicyPanelProps {
  policy: Policy | null;
  summaries: SpendSummary[];
  loading: boolean;
}

export function PolicyPanel(props: PolicyPanelProps) {
  return <PolicyOverview {...props} pendingCount={0} />;
}
