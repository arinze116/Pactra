import { Status } from "./UI";
import type { TransactionStatus } from "../types";
export function DecisionStatus({ status }: { status: TransactionStatus }) { return <Status value={status} />; }
