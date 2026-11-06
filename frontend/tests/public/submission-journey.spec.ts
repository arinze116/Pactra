import { expect, test, type Page } from "@playwright/test";

const password = "SubmissionSmoke2026!";

async function register(page: Page, label: string) {
  const email = `pactra-public-smoke-${label}-${Date.now()}-${Math.random().toString(16).slice(2)}@example.com`;
  await page.goto("/sign-up");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Create sandbox account" }).click();
  await expect(page).toHaveURL(/\/app$/);
  return email;
}

async function login(page: Page, email: string) {
  await page.goto("/sign-in");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
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
  if ((await submit.textContent())?.includes("Review")) {
    await submit.click();
    await page.getByRole("button", { name: "Confirm and create request" }).click();
    return;
  }
  await submit.click();
}

test("public submission journey remains secure, durable, and tenant isolated", async ({ page, request }) => {
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
  const primaryReceipt = page.url();

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
  await page.goto("/app/approvals");
  await page.getByRole("article").filter({ hasText: "Ada Public Smoke" }).getByRole("button", { name: "Approve" }).click();
  await expect(page.getByText("No requests need approval")).toBeVisible();

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

  const missingCsrf = await page.evaluate(async () => {
    const response = await fetch("/api/wallet/topups", {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ amount_cents: 100, idempotency_key: crypto.randomUUID() }),
    });
    const payload = await response.json();
    return { status: response.status, code: payload.error?.code };
  });
  expect(missingCsrf).toEqual({ status: 403, code: "CSRF_INVALID" });

  await page.getByRole("link", { name: "Assistant" }).first().click();
  await page.getByLabel("Message Pactra").fill("Pay Notion $20 for our software subscription");
  await page.getByRole("button", { name: "Send message" }).click();
  await expect(page.locator(".assistant-message-assistant").getByText(/Payment to Notion completed after backend policy and ledger confirmation/)).toBeVisible();

  await page.getByRole("link", { name: "Wallet" }).first().click();
  await page.getByLabel("Type RESET").fill("RESET");
  await page.getByRole("button", { name: "Reset sandbox" }).click();
  await expect(page.getByText("$1,000.00").first()).toBeVisible();

  await logout(page);
  const loggedOutStatus = await page.evaluate(async () => (await fetch("/api/auth/me", { credentials: "include" })).status);
  expect(loggedOutStatus).toBe(401);

  await login(page, primaryEmail);
  await page.goto(primaryReceipt);
  await expect(page.getByText("Linear Public Smoke")).toBeVisible();

  await logout(page);
  await register(page, "other");
  await page.goto(primaryReceipt);
  await expect(page.getByText("Transaction not found")).toBeVisible();
});
