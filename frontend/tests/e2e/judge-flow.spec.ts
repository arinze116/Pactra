import { expect, test, type Page } from "@playwright/test";
import { execFileSync } from "node:child_process";

const password = "JudgePassword2026!";

async function register(page: Page, prefix: string) {
  const email = `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}@example.com`;
  await page.goto("/sign-up");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Create sandbox account" }).click();
  await expect(page).toHaveURL(/\/app$/);
  return email;
}

async function submitPayment(page: Page) {
  const submit = page.getByRole("button", { name: /Review request|Create payment request/ });
  await expect(submit).toBeVisible();
  if ((await submit.textContent())?.includes("Review")) {
    await submit.click();
    await page.getByRole("button", { name: "Confirm and create request" }).click();
    return;
  }
  await submit.click();
}

async function expectNoHorizontalOverflow(page: Page) {
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  expect(overflow).toBeLessThanOrEqual(1);
}

async function exercisePasswordReveal(page: Page, viewport: { width: number; height: number }, prefix: string) {
  await page.setViewportSize(viewport);
  const email = `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}@example.com`;
  await page.goto("/sign-up");
  const signUpPassword = page.getByLabel("Password", { exact: true });
  await page.getByLabel("Email").fill(email);
  await signUpPassword.fill(password);
  await signUpPassword.evaluate((input: HTMLInputElement) => input.setSelectionRange(5, 10));
  const showSignUp = page.getByRole("button", { name: "Show password" });
  await showSignUp.focus();
  await showSignUp.press("Space");
  await expect(page.getByRole("button", { name: "Hide password" })).toHaveAttribute("aria-pressed", "true");
  await expect(signUpPassword).toHaveAttribute("type", "text");
  await expect(signUpPassword).toHaveValue(password);
  await expect(signUpPassword).toBeFocused();
  expect(await signUpPassword.evaluate((input: HTMLInputElement) => [input.selectionStart, input.selectionEnd])).toEqual([5, 10]);
  await page.getByRole("button", { name: "Create sandbox account" }).click();
  await expect(page).toHaveURL(/\/app$/);

  await page.goto("/app/settings");
  await page.getByRole("button", { name: "Sign out of this session" }).click();
  await page.getByLabel("Email").fill(email);
  const signInPassword = page.getByLabel("Password", { exact: true });
  await signInPassword.fill(password);
  const showSignIn = page.getByRole("button", { name: "Show password" });
  await showSignIn.focus();
  await showSignIn.press("Enter");
  await expect(page.getByRole("button", { name: "Hide password" })).toHaveAttribute("aria-pressed", "true");
  await expect(signInPassword).toHaveAttribute("type", "text");
  await expect(signInPassword).toHaveValue(password);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page).toHaveURL(/\/app$/);
}

test("password reveal remains accessible through sign-up and sign-in", async ({ page }) => {
  await exercisePasswordReveal(page, { width: 1440, height: 900 }, "judge-reveal-desktop");
  await page.goto("/app/settings");
  await page.getByRole("button", { name: "Sign out of this session" }).click();
  await exercisePasswordReveal(page, { width: 390, height: 844 }, "judge-reveal-mobile");
});

test("fresh judge completes the core sandbox journey", async ({ page }) => {
  await register(page, "judge-core");
  await expect(page.getByText("$1,000.00").first()).toBeVisible();

  await page.getByRole("link", { name: "Wallet" }).first().click();
  let loseFirstTopUpResponse = true;
  await page.route("**/api/wallet/topups", async (route) => {
    if (loseFirstTopUpResponse) {
      loseFirstTopUpResponse = false;
      await route.fetch();
      await route.abort("failed");
      return;
    }
    await route.continue();
  });
  page.once("dialog", (dialog) => dialog.accept());
  await page.getByRole("button", { name: "$100.00" }).click();
  await expect(page.getByText("Failed to fetch")).toBeVisible();
  page.once("dialog", (dialog) => dialog.accept());
  await page.getByRole("button", { name: "$100.00" }).click();
  await expect(page.getByText("$1,100.00").first()).toBeVisible();
  await expect(page.getByText("$1,200.00")).toHaveCount(0);
  await page.unroute("**/api/wallet/topups");

  await page.getByRole("link", { name: "New payment" }).first().click();
  await page.getByLabel("Vendor or recipient name").fill("Linear");
  await page.getByLabel("Amount (USD)").fill("49.00");
  await page.getByLabel("Category").selectOption("software");
  await page.getByLabel("Business reason").fill("Monthly software subscription");
  await submitPayment(page);
  await expect(page).toHaveURL(/\/app\/transactions\//);
  await expect(page.getByText("Completed").first()).toBeVisible();
  await expect(page.getByText("Internal ledger capture")).toBeVisible();
  await expect(page.getByText("Not applicable — internal ledger only")).toBeVisible();
  await expect(page.getByText("SUCCESS", { exact: true })).toHaveCount(0);

  await page.getByRole("link", { name: "New payment" }).first().click();
  await page.getByRole("button", { name: "Payout" }).click();
  await page.getByLabel("Vendor or recipient name").fill("Ada Contractor");
  await page.getByLabel("Amount (USD)").fill("125.00");
  await page.getByLabel("Recipient email").fill("ada@example.com");
  await page.getByLabel("Category").selectOption("freelance");
  await page.getByLabel("Business reason").fill("Contract work");
  await submitPayment(page);
  await expect(page.getByText("Needs approval").first()).toBeVisible();
  const payoutReceipt = page.url();
  await expect(page.getByText("ada@example.com", { exact: true })).toBeVisible();

  await page.goto("/app/approvals");
  await expect(page.getByText("Ada Contractor")).toBeVisible();
  await page.getByRole("button", { name: "Approve" }).click();
  await expect(page.getByText("No requests need approval")).toBeVisible();
  await page.goto(payoutReceipt);
  await expect(page.getByText("ada@example.com", { exact: true })).toBeVisible();

  await page.getByRole("link", { name: "Assistant" }).first().click();
  await page.getByLabel("Message Pactra").fill("Pay Notion $20 for our software subscription");
  await page.getByRole("button", { name: "Send message" }).click();
  await expect(page.locator(".assistant-message-assistant").getByText(/Payment to Notion completed after backend policy and ledger confirmation/)).toBeVisible();
  await expect(page.getByRole("link", { name: "Open verified receipt" })).toBeVisible();

  await page.getByRole("link", { name: "Wallet" }).first().click();
  await page.getByLabel("Type RESET").fill("RESET");
  await page.getByRole("button", { name: "Reset sandbox" }).click();
  await expect(page.getByText("$1,000.00").first()).toBeVisible();
});

test("policy changes, blocked requests and rejection remain auditable", async ({ page }) => {
  await register(page, "judge-policy");

  await page.getByRole("link", { name: "Policies" }).first().click();
  await page.getByLabel("Approval above").fill("25.00");
  await page.getByLabel("Allowed categories").fill("ops, software, cloud, freelance, marketing");
  await page.getByLabel("Allowed categories").press("Tab");
  await expect(page.getByLabel("marketing")).toHaveValue("100.00");
  await page.getByRole("button", { name: "Save policy" }).click();
  await expect(page.getByText("Policy version 2 saved")).toBeVisible();
  await expect(page.getByText(/Version 2/)).toBeVisible();

  await page.goto("/app/payments/new?scenario=auto");
  await expect(page.getByText("Likely needs approval")).toBeVisible();
  await submitPayment(page);
  await expect(page.getByText("Needs approval").first()).toBeVisible();

  await page.goto("/app/payments/new?scenario=blocked");
  await submitPayment(page);
  await expect(page.getByText("Blocked").first()).toBeVisible();
  await expect(page.getByText("TRANSACTION_LIMIT_EXCEEDED", { exact: false })).toBeVisible();

  await page.goto("/app/approvals");
  const pendingCard = page.getByRole("article").filter({ hasText: "Linear" });
  await expect(pendingCard.getByText(/judge-policy-.*@example\.com/)).toBeVisible();
  await expect(pendingCard.getByText("Available balance")).toBeVisible();
  await expect(pendingCard.getByText("Policy checks")).toBeVisible();
  await expect(pendingCard.getByText("Age")).toBeVisible();
  await pendingCard.getByRole("button", { name: "Reject" }).click();
  await pendingCard.getByLabel("Rejection reason for Linear").fill("Invoice needs correction");
  await pendingCard.getByRole("button", { name: "Confirm rejection" }).click();
  await expect(pendingCard).not.toBeVisible();
});

test("overview and wallet sections recover independently", async ({ page }) => {
  await register(page, "judge-partial-recovery");
  await expect(page.getByText("$1,000.00").first()).toBeVisible();

  const overviewCases = [
    { pattern: "**/api/wallet", method: "GET", retry: "Retry wallet" },
    { pattern: "**/api/spend-summary", method: "GET", retry: "Retry spend summary" },
    { pattern: "**/api/transactions?limit=100", method: "GET", retry: "Retry transactions" },
    { pattern: "**/api/approvals", method: "GET", retry: "Retry approvals" },
  ] as const;
  for (const recoveryCase of overviewCases) {
    let shouldFail = true;
    await page.route(recoveryCase.pattern, async (route) => {
      if (shouldFail && route.request().method() === recoveryCase.method) {
        shouldFail = false;
        await route.abort("failed");
        return;
      }
      await route.continue();
    });
    await page.reload();
    await expect(page.getByRole("button", { name: recoveryCase.retry })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Recent transactions" })).toBeVisible();
    await page.getByRole("button", { name: recoveryCase.retry }).click();
    await expect(page.getByRole("button", { name: recoveryCase.retry })).toHaveCount(0);
    await page.unroute(recoveryCase.pattern);
  }

  await page.goto("/app/wallet");
  for (const recoveryCase of [
    { pattern: "**/api/wallet", retry: "Retry wallet" },
    { pattern: "**/api/wallet/ledger?limit=100", retry: "Retry ledger" },
  ] as const) {
    let shouldFail = true;
    await page.route(recoveryCase.pattern, async (route) => {
      if (shouldFail && route.request().method() === "GET") {
        shouldFail = false;
        await route.abort("failed");
        return;
      }
      await route.continue();
    });
    await page.reload();
    await expect(page.getByRole("button", { name: recoveryCase.retry })).toBeVisible();
    await page.getByRole("button", { name: recoveryCase.retry }).click();
    await expect(page.getByRole("button", { name: recoveryCase.retry })).toHaveCount(0);
    await page.unroute(recoveryCase.pattern);
  }
});

test("guided insufficient-funds outcome and internal reversal remain auditable", async ({ page }) => {
  await register(page, "judge-controls");
  await page.goto("/app/payments/new?scenario=insufficient");
  await page.getByRole("button", { name: "Run insufficient-funds test" }).click();
  await expect(page).toHaveURL(/\/app\/transactions\//);
  await expect(page.getByText("INSUFFICIENT_FUNDS", { exact: true })).toBeVisible();
  await expect(page.getByText("No ledger posting has occurred", { exact: false })).toBeVisible();

  await page.goto("/app/payments/new?scenario=auto");
  await submitPayment(page);
  await expect(page.getByRole("button", { name: "Reverse" })).toBeVisible();
  const transactionUrl = page.url();
  const transactionId = transactionUrl.split("/").pop();
  page.once("dialog", (dialog) => dialog.accept());
  await page.getByRole("button", { name: "Reverse" }).click();
  await expect(page.getByText("Reversed").first()).toBeVisible();
  await expect(page.getByText("Compensating sandbox reversal posted")).toBeVisible();
  await expect(page.getByText(/\$98\.00 debits = \$98\.00 credits/)).toBeVisible();

  const csrf = (await page.context().cookies()).find((cookie) => cookie.name === "pactra_csrf")?.value;
  expect(csrf).toBeTruthy();
  const second = await page.request.post(`http://127.0.0.1:8000/api/transactions/${transactionId}/reverse`, {
    headers: { Origin: "http://127.0.0.1:5173", "X-CSRF-Token": csrf ?? "" },
    data: { idempotency_key: "browser-second-reversal-0001", reason: "Must fail" },
  });
  expect(second.status()).toBe(409);
  expect((await second.json()).error.code).toBe("NOT_REVERSIBLE");
});

test("failed internal retry is idempotent through the browser path", async ({ page }) => {
  const email = await register(page, "judge-browser-retry");
  const python = process.env.E2E_RESOLVED_PYTHON;
  const databaseUrl = process.env.E2E_RESOLVED_DATABASE_URL;
  expect(python).toBeTruthy();
  expect(databaseUrl).toBeTruthy();
  const transactionId = execFileSync(
    python ?? "python",
    ["-m", "scripts.seed_e2e_failed_transaction", email],
    {
      cwd: "..",
      encoding: "utf8",
      env: {
        ...process.env,
        APP_ENV: "test",
        DATABASE_URL: databaseUrl ?? "",
        PAYPAL_MOCK_MODE: "false",
        SESSION_COOKIE_SECURE: "false",
      },
    },
  ).trim();

  let retryKey = "";
  await page.route(`**/api/transactions/${transactionId}/retry`, async (route) => {
    retryKey = (route.request().postDataJSON() as { idempotency_key: string }).idempotency_key;
    await route.continue();
  });
  await page.goto(`/app/transactions/${transactionId}`);
  await page.getByRole("button", { name: "Retry" }).click();
  await expect(page.getByText("Completed").first()).toBeVisible();
  await expect(page.getByText("Internal ledger capture")).toBeVisible();
  expect(retryKey).toMatch(/^retry-/);

  const csrf = (await page.context().cookies()).find((cookie) => cookie.name === "pactra_csrf")?.value;
  const replay = await page.request.post(`http://127.0.0.1:8000/api/transactions/${transactionId}/retry`, {
    headers: { Origin: "http://127.0.0.1:5173", "X-CSRF-Token": csrf ?? "" },
    data: { idempotency_key: retryKey },
  });
  expect(replay.status()).toBe(202);
  expect((await replay.json()).transaction.id).toBe(transactionId);
  await page.reload();
  await expect(page.getByText("Internal ledger capture")).toHaveCount(1);
});

test("another signed-in user cannot open a private receipt", async ({ page }) => {
  await register(page, "judge-owner");
  await page.goto("/app/payments/new?scenario=auto");
  await submitPayment(page);
  await expect(page).toHaveURL(/\/app\/transactions\//);
  const privateReceipt = page.url();

  await page.goto("/app/settings");
  await expect(page).toHaveURL(/\/app\/settings$/);
  await page.getByRole("button", { name: "Sign out of this session" }).click();
  await register(page, "judge-other");
  await page.goto(privateReceipt);
  await expect(page.getByText("Transaction not found")).toBeVisible();
});

test("transaction history recovers when optional provider status is unavailable", async ({ page }) => {
  await page.route("**/api/integrations/paypal/status", (route) => route.abort("failed"));
  await register(page, "judge-recovery");
  await expect(page.getByText("$1,000.00").first()).toBeVisible();
  await expect(page.getByText(/Status could not be verified/)).toBeVisible();

  await page.getByRole("link", { name: "New payment" }).first().click();
  await expect(page.getByText(/Internal sandbox payments remain available/)).toBeVisible();
  await expect(page.getByRole("button", { name: "Create payment request" })).toBeEnabled();

  let shouldFail = true;
  await page.route("**/api/transactions**", async (route) => {
    if (shouldFail) {
      await route.abort("failed");
      return;
    }
    await route.continue();
  });
  await page.goto("/app/transactions");
  await expect(page.getByText("Failed to fetch")).toBeVisible();
  shouldFail = false;
  await page.getByRole("button", { name: "Try again" }).click();
  await expect(page.getByText("No matching transactions")).toBeVisible();

  await page.unroute("**/api/transactions**");
  const firstPage = {
    id: "11111111-1111-4111-8111-111111111111",
    type: "vendor_payment",
    vendor: "Page One Vendor",
    recipient: null,
    amount_cents: 4_900,
    currency: "USD",
    category: "marketing",
    reason: "Pagination test",
    status: "completed",
    sandbox_generation: 1,
    policy_version: 1,
    rail: "internal_sandbox",
    rail_reference: null,
    provider_batch_id: null,
    provider_item_id: null,
    provider_status: null,
    failure_code: null,
    created_at: "2026-11-05T00:00:00Z",
    updated_at: "2026-11-05T00:00:00Z",
    completed_at: "2026-11-05T00:00:00Z",
  };
  await page.route("**/api/transactions?**", async (route) => {
    const cursor = new URL(route.request().url()).searchParams.get("cursor");
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(cursor
        ? { items: [{ ...firstPage, id: "22222222-2222-4222-8222-222222222222", vendor: "Page Two Vendor", status: "cancelled" }], next_cursor: null }
        : { items: [firstPage], next_cursor: "next-page" }),
    });
  });
  await page.reload();
  await expect(page.getByRole("gridcell", { name: "Page One Vendor" })).toBeVisible();
  await expect(page.getByLabel("Category").locator('option[value="marketing"]')).toHaveCount(1);
  await page.getByRole("button", { name: "Load more transactions" }).click();
  await expect(page.getByRole("gridcell", { name: "Page Two Vendor" })).toBeVisible();
  await expect(page.getByText("2 loaded records")).toBeVisible();
});

test("ambiguous payment retry survives reload without creating a duplicate", async ({ page }) => {
  await register(page, "judge-payment-retry");
  await page.getByRole("link", { name: "New payment" }).first().click();
  await page.getByLabel("Vendor or recipient name").fill("Linear");
  await page.getByLabel("Amount (USD)").fill("49.00");
  await page.getByLabel("Category").selectOption("software");
  await page.getByLabel("Business reason").fill("Monthly software subscription");

  const requestKeys: string[] = [];
  let loseFirstResponse = true;
  await page.route("**/api/transactions", async (route) => {
    if (route.request().method() !== "POST") {
      await route.continue();
      return;
    }
    const payload = route.request().postDataJSON() as { idempotency_key: string };
    requestKeys.push(payload.idempotency_key);
    if (loseFirstResponse) {
      loseFirstResponse = false;
      await route.fetch();
      await route.abort("failed");
      return;
    }
    await route.continue();
  });

  await submitPayment(page);
  await expect(page.getByText("Payment request could not be created")).toBeVisible();
  const storedAttempt = await page.evaluate(() => {
    const storageKey = Object.keys(sessionStorage).find((key) => key.startsWith("pactra-payment-attempt:"));
    return storageKey ? JSON.parse(sessionStorage.getItem(storageKey) ?? "null") as Record<string, string> : null;
  });
  expect(storedAttempt).not.toBeNull();
  expect(Object.keys(storedAttempt ?? {}).sort()).toEqual(["digest", "key"]);
  expect(JSON.stringify(storedAttempt)).not.toContain("Linear");

  await page.reload();
  await expect(page.getByLabel("Vendor or recipient name")).toHaveValue("Linear");
  await submitPayment(page);
  await expect(page).toHaveURL(/\/app\/transactions\//);
  expect(requestKeys).toHaveLength(2);
  expect(requestKeys[1]).toBe(requestKeys[0]);

  await page.unroute("**/api/transactions");
  await page.goto("/app/transactions");
  await expect(page.getByRole("gridcell", { name: "Linear" })).toHaveCount(1);
});

test("credential errors and failed logout do not discard a valid session", async ({ page }) => {
  const email = await register(page, "judge-auth-errors");
  await page.goto("/app/settings");
  await page.getByLabel("Current password").fill("WrongCurrentPassword2026!");
  await page.getByLabel("New password").fill("DifferentJudgePassword2026!");
  await page.getByRole("button", { name: "Change password" }).click();
  await expect(page.getByText("Current password is incorrect.")).toBeVisible();
  await expect(page).toHaveURL(/\/app\/settings$/);
  await expect(page.getByText(email).last()).toBeVisible();

  await page.route("**/api/auth/logout", (route) => route.abort("failed"));
  await page.getByRole("button", { name: "Sign out of this session" }).click();
  await expect(page.getByText("Failed to fetch")).toBeVisible();
  await expect(page).toHaveURL(/\/app\/settings$/);
  await page.unroute("**/api/auth/logout");

  await page.getByRole("link", { name: "Wallet" }).first().click();
  await expect(page.getByRole("heading", { name: "Sandbox wallet" })).toBeVisible();
});

test("assistant conversations persist, continue, and retry without duplicates", async ({ page }) => {
  await register(page, "judge-conversation");
  await page.getByRole("link", { name: "Assistant" }).first().click();

  const composer = page.getByLabel("Message Pactra");
  await composer.fill("Please take care");
  await composer.press("Shift+Enter");
  await composer.type("of the invoice");
  await expect(composer).toHaveValue("Please take care\nof the invoice");
  await composer.press("Enter");
  await expect(page.locator(".assistant-message-assistant").getByText(/couldn't identify the amount or recipient/i)).toBeVisible();
  await expect(page).toHaveURL(/\/app\/assistant\/[a-f0-9-]+$/);
  const conversationUrl = page.url();

  await page.reload();
  await expect(page.locator(".assistant-message-user").getByText("Please take care", { exact: false })).toBeVisible();
  await expect(page.locator(".assistant-message-assistant").getByText(/couldn't identify the amount or recipient/i)).toBeVisible();

  let failAfterBackend = true;
  await page.route("**/api/chat", async (route) => {
    if (failAfterBackend) {
      failAfterBackend = false;
      await route.fetch();
      await route.abort("failed");
      return;
    }
    await route.continue();
  });
  const retryText = "Pay Linear $49 for our software subscription";
  await composer.fill(retryText);
  await composer.press("Enter");
  await expect(page.getByText("Failed to fetch")).toBeVisible();
  await expect(composer).toHaveValue(retryText);
  await composer.press("Enter");
  await expect(page.locator(".assistant-message-assistant").getByText(/Payment to Linear completed after backend policy and ledger confirmation/)).toBeVisible();
  await page.unroute("**/api/chat");

  await page.goto("/app/assistant");
  await expect(page.locator(".assistant-history-row").getByText("Please take care of the invoice", { exact: true })).toBeVisible();
  await page.goto(conversationUrl);
  await expect(page.locator(".assistant-message-user").getByText(retryText, { exact: true })).toHaveCount(1);
});

test("policy editor rejects invalid state and only confirms persisted saves", async ({ page }) => {
  await register(page, "judge-policy-save");
  await page.getByRole("link", { name: "Policies" }).first().click();

  const save = page.getByRole("button", { name: "Save policy" });
  const daily = page.getByLabel("Daily limit");
  await expect(save).toBeDisabled();
  await daily.fill("");
  await expect(page.getByText(/Enter an amount greater than \$0/)).toBeVisible();
  await expect(page.getByText("Policy needs attention")).toBeVisible();
  await expect(save).toBeDisabled();

  await daily.fill("600.00");
  await expect(save).toBeEnabled();
  await page.route("**/api/policy", async (route) => {
    if (route.request().method() === "PUT") {
      await route.fulfill({
        status: 503,
        contentType: "application/json",
        body: JSON.stringify({ error: { code: "TEMPORARY_FAILURE", message: "Temporary save failure" } }),
      });
      return;
    }
    await route.continue();
  });
  await save.click();
  await expect(page.getByText("Temporary save failure")).toBeVisible();
  await expect(daily).toHaveValue("600.00");
  await expect(page.getByText(/Policy version 2 saved/)).toHaveCount(0);

  await page.unroute("**/api/policy");
  await save.click();
  await expect(page.getByText("Policy version 2 saved")).toBeVisible();
  await page.reload();
  await expect(daily).toHaveValue("600.00");
  await expect(page.getByText("Version 2")).toBeVisible();
  await expect(save).toBeDisabled();
});

test.describe("mobile judge navigation", () => {
  test.use({ viewport: { width: 390, height: 844 } });

  test("public and authenticated navigation fit a 390px viewport", async ({ page }) => {
    const email = `judge-mobile-${Date.now()}-${Math.random().toString(16).slice(2)}@example.com`;
    await page.goto("/");
    await expectNoHorizontalOverflow(page);

    await page.getByRole("button", { name: "Open navigation" }).click();
    await expect(page.getByRole("link", { name: "Create sandbox" })).toBeVisible();
    await expectNoHorizontalOverflow(page);
    await page.getByRole("link", { name: "Create sandbox" }).click();

    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Password", { exact: true }).fill(password);
    await page.getByRole("button", { name: "Create sandbox account" }).click();
    await expect(page).toHaveURL(/\/app$/);
    await expectNoHorizontalOverflow(page);

    await page.getByRole("button", { name: "Open navigation" }).click();
    await page.getByRole("link", { name: "Settings" }).click();
    await page.getByRole("button", { name: "Sign out of this session" }).click();
    await expect(page).toHaveURL(/\/sign-in$/);

    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Password", { exact: true }).fill(password);
    await page.getByRole("button", { name: "Sign in", exact: true }).click();
    await expect(page).toHaveURL(/\/app$/);
    await expectNoHorizontalOverflow(page);

    await page.getByRole("button", { name: "Open navigation" }).click();
    await expect(page.getByText(email).last()).toBeVisible();
    await page.getByRole("link", { name: "Wallet" }).click();
    await expect(page).toHaveURL(/\/app\/wallet$/);
    await expect(page.getByRole("heading", { name: "Sandbox wallet" })).toBeVisible();
    await expectNoHorizontalOverflow(page);

    await page.getByRole("button", { name: "Open navigation" }).click();
    await page.getByRole("link", { name: "New payment" }).click();
    await expect(page.getByRole("heading", { name: "New payment" })).toBeVisible();
    await expectNoHorizontalOverflow(page);
  });
});
