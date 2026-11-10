import { expect, test, type Page } from "@playwright/test";

const password = "SubmissionSmoke2026!";

async function register(page: Page, label: string) {
  const email = `pactra-public-smoke-${label}-${Date.now()}-${Math.random().toString(16).slice(2)}@example.com`;
  await page.goto("/sign-up");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Create sandbox account" }).click();
  await expect(page).toHaveURL(/\/app$/);
  return email;
}

async function login(page: Page, email: string) {
  await page.goto("/sign-in");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page).toHaveURL(/\/app$/);
}

async function logout(page: Page) {
  await page.goto("/app/settings");
  await page.getByRole("button", { name: "Sign out of this session" }).click();
  await expect(page).toHaveURL(/\/sign-in$/);
}

async function submitPayment(page: Page) {
  const submit = page.getByRole("button", { name: /Review request|Create payment request/ });
  await expect(submit).toBeEnabled();
  await submit.click();
  const confirmation = page.getByRole("button", { name: "Confirm and create request" });
  const needsConfirmation = await confirmation
    .waitFor({ state: "visible", timeout: 1_500 })
    .then(() => true)
    .catch(() => false);
  if (needsConfirmation) await confirmation.click();
}

test("public submission journey remains secure, durable, and tenant isolated", async ({ page, request }) => {
  const consoleErrors: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text().slice(0, 500));
  });
  await page.goto("/");
  await expect(page).toHaveTitle(/Pactra/);
  await expect(page.getByRole("heading", { name: /Control the spend/ })).toBeVisible();

  const readiness = await request.get("/api/ready");
  expect(readiness.status()).toBe(200);
  expect(await readiness.json()).toMatchObject({
    status: "ready",
    database: "ok",
    sandbox_mode: true,
    internal_sandbox_available: true,
    ai_enabled: false,
    paypal_payouts_configured: false,
  });

  const primaryEmail = await register(page, "owner");
  await expect(page.getByText("$1,000.00").first()).toBeVisible();

  const cookies = await page.context().cookies();
  for (const name of ["pactra_session", "pactra_csrf"]) {
    const cookie = cookies.find((candidate) => candidate.name === name);
    expect(cookie, `${name} should be set`).toBeDefined();
    expect(cookie?.httpOnly).toBe(true);
    expect(cookie?.secure).toBe(true);
    expect(cookie?.sameSite).toBe("Lax");
  }

  await page.getByRole("link", { name: "Wallet" }).first().click();
  page.once("dialog", (dialog) => dialog.accept());
  await page.getByRole("button", { name: "$100.00" }).click();
  await expect(page.getByText("$1,100.00").first()).toBeVisible();
  await expect(page.getByRole("heading", { name: "Ledger history" })).toBeVisible();

  await page.getByRole("link", { name: "Policies" }).first().click();
  await page.getByLabel("Approval above").fill("50.00");
  await page.getByRole("button", { name: "Save policy" }).click();
  await expect(page.getByText("Policy version 2 saved")).toBeVisible();
  const ownerPolicyResponse = await page.context().request.get("/api/policy");
  expect(ownerPolicyResponse.status()).toBe(200);
  const ownerPolicyId = ((await ownerPolicyResponse.json()) as { id: string }).id;

  await page.getByRole("link", { name: "New payment" }).first().click();
  await page.getByLabel("Vendor or recipient name").fill("Linear Public Smoke");
  await page.getByLabel("Amount (USD)").fill("49.00");
  await page.getByLabel("Category").selectOption("software");
  await page.getByLabel("Business reason").fill("Submission verification software expense");
  await submitPayment(page);
  await expect(page.getByRole("heading", { name: "Transaction receipt" })).toBeVisible();
  await expect(page.getByText("Completed").first()).toBeVisible();
  await expect(page.getByRole("heading", { name: "Lifecycle" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Ledger impact" })).toBeVisible();
  await expect(page.getByText("Internal ledger capture")).toBeVisible();
  await expect(page.getByText("Not applicable: internal ledger only")).toBeVisible();
  await expect(page.getByText("SUCCESS", { exact: true })).toHaveCount(0);
  const primaryReceipt = page.url();
  const ownerCompletedId = primaryReceipt.split("/").pop() ?? "";

  await page.reload();
  await expect(page.getByText("Linear Public Smoke")).toBeVisible();
  await expect(page.getByText("Completed").first()).toBeVisible();

  await page.getByRole("link", { name: "New payment" }).first().click();
  await page.getByRole("button", { name: "Payout" }).click();
  await page.getByLabel("Vendor or recipient name").fill("Ada Public Smoke");
  await page.getByLabel("Amount (USD)").fill("125.00");
  await page.getByLabel("Recipient email").fill("ada-public-smoke@example.com");
  await page.getByLabel("Category").selectOption("freelance");
  await page.getByLabel("Business reason").fill("Submission verification contract work");
  await submitPayment(page);
  await expect(page.getByText("Needs approval").first()).toBeVisible();
  const ownerApprovalReceipt = page.url();
  const ownerApprovalId = ownerApprovalReceipt.split("/").pop() ?? "";
  await expect(page.getByText("ada-public-smoke@example.com", { exact: true })).toBeVisible();
  await page.goto("/app/approvals");
  await page.getByRole("article").filter({ hasText: "Ada Public Smoke" }).getByRole("button", { name: "Approve" }).click();
  await expect(page.getByText("No requests need approval")).toBeVisible();
  await page.goto(ownerApprovalReceipt);
  await expect(page.getByText("ada-public-smoke@example.com", { exact: true })).toBeVisible();

  await page.goto("/app/payments/new?scenario=reject");
  await page.getByLabel("Category").selectOption("ops");
  await submitPayment(page);
  await expect(page.getByText("Needs approval").first()).toBeVisible();
  await page.goto("/app/approvals");
  const rejectedRequest = page.getByRole("article").filter({ hasText: "Contractor" });
  await rejectedRequest.getByRole("button", { name: "Reject" }).click();
  await rejectedRequest.getByLabel("Rejection reason for Contractor").fill("Submission verification rejection");
  await rejectedRequest.getByRole("button", { name: "Confirm rejection" }).click();
  await expect(rejectedRequest).not.toBeVisible();

  await page.goto("/app/payments/new?scenario=blocked");
  await submitPayment(page);
  await expect(page.getByText("Blocked").first()).toBeVisible();
  await expect(page.getByText("TRANSACTION_LIMIT_EXCEEDED")).toBeVisible();
  await expect(page.getByText("No posted ledger entries")).toBeVisible();

  const missingCsrfResponse = await page.context().request.post("/api/wallet/topups", {
    headers: { Origin: new URL(page.url()).origin },
    data: { amount_cents: 100, idempotency_key: crypto.randomUUID() },
  });
  const missingCsrfPayload = (await missingCsrfResponse.json()) as { error?: { code?: string } };
  const missingCsrf = {
    status: missingCsrfResponse.status(),
    code: missingCsrfPayload.error?.code,
  };
  expect(missingCsrf).toEqual({ status: 403, code: "CSRF_INVALID" });

  await page.getByRole("link", { name: "Assistant" }).first().click();
  await page.getByLabel("Message Pactra").fill("Pay Notion $20 for our software subscription");
  await page.getByRole("button", { name: "Send message" }).click();
  await expect(page.locator(".assistant-message-assistant").getByText(/Payment to Notion completed after backend policy and ledger confirmation/)).toBeVisible();
  const ownerConversationsResponse = await page.context().request.get("/api/conversations");
  expect(ownerConversationsResponse.status()).toBe(200);
  const ownerConversationId = ((await ownerConversationsResponse.json()) as { items: Array<{ id: string }> }).items[0].id;

  await page.getByRole("link", { name: "Wallet" }).first().click();
  await page.getByLabel("Type RESET").fill("RESET");
  await page.getByRole("button", { name: "Reset sandbox" }).click();
  await expect(page.getByText("$1,000.00").first()).toBeVisible();

  await logout(page);
  const loggedOutStatus = (await page.context().request.get("/api/auth/me")).status();
  expect(loggedOutStatus).toBe(401);

  await login(page, primaryEmail);
  await page.goto(primaryReceipt);
  await expect(page.getByText("Linear Public Smoke")).toBeVisible();

  await logout(page);
  await register(page, "other");
  const api = page.context().request;
  const sessionResponse = await api.get("/api/auth/session");
  expect(sessionResponse.status()).toBe(200);
  const csrf = sessionResponse.headers()["x-csrf-token"] ?? "";
  expect(csrf).not.toBe("");
  const origin = new URL(page.url()).origin;
  const mutate = async (path: string, body?: Record<string, unknown>) => {
    const response = await api.post(path, {
      headers: { Origin: origin, "X-CSRF-Token": csrf },
      ...(body ? { data: body } : {}),
    });
    return response.status();
  };
  const [transactionsResponse, approvalsResponse, policiesResponse, conversationsResponse] = await Promise.all([
    api.get("/api/transactions?generation=all"),
    api.get("/api/approvals"),
    api.get("/api/policies"),
    api.get("/api/conversations?include_archived=true"),
  ]);
  const transactions = (await transactionsResponse.json()) as { items: Array<{ id: string }> };
  const approvals = (await approvalsResponse.json()) as { items: Array<{ id: string }> };
  const policies = (await policiesResponse.json()) as { items: Array<{ id: string }> };
  const conversations = (await conversationsResponse.json()) as { items: Array<{ id: string }> };
  const conversationPatch = await api.patch(`/api/conversations/${ownerConversationId}`, {
    headers: { Origin: origin, "X-CSRF-Token": csrf },
    data: { title: "Cross-tenant mutation" },
  });
  const isolation = {
    ownerIdsVisible: transactions.items.some((item) => [ownerCompletedId, ownerApprovalId].includes(item.id)),
    ownerApprovalVisible: approvals.items.some((item) => item.id === ownerApprovalId),
    ownerPolicyVisible: policies.items.some((item) => item.id === ownerPolicyId),
    ownerConversationVisible: conversations.items.some((item) => item.id === ownerConversationId),
    receipt: (await api.get(`/api/transactions/${ownerCompletedId}`)).status(),
    conversation: (await api.get(`/api/conversations/${ownerConversationId}/messages`)).status(),
    conversationPatch: conversationPatch.status(),
    approve: await mutate(`/api/approvals/${ownerApprovalId}/approve`, { idempotency_key: "public-cross-approve-0001" }),
    reject: await mutate(`/api/approvals/${ownerApprovalId}/reject`, { idempotency_key: "public-cross-reject-0001", reason: "Unauthorized" }),
    reverse: await mutate(`/api/transactions/${ownerCompletedId}/reverse`, { idempotency_key: "public-cross-reverse-0001", reason: "Unauthorized" }),
    retry: await mutate(`/api/transactions/${ownerCompletedId}/retry`, { idempotency_key: "public-cross-retry-0001" }),
    reconcile: await mutate(`/api/transactions/${ownerCompletedId}/reconcile`),
  };
  expect(isolation).toEqual({
    ownerIdsVisible: false,
    ownerApprovalVisible: false,
    ownerPolicyVisible: false,
    ownerConversationVisible: false,
    receipt: 404,
    conversation: 404,
    conversationPatch: 404,
    approve: 404,
    reject: 404,
    reverse: 404,
    retry: 404,
    reconcile: 404,
  });
  expect(consoleErrors).toEqual([]);
  await page.goto(primaryReceipt);
  await expect(page.getByText("Transaction not found")).toBeVisible();
});
