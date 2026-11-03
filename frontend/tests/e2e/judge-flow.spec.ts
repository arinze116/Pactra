import { expect, test, type Page } from "@playwright/test";

const password = "JudgePassword2026!";

async function register(page: Page, prefix: string) {
  const email = `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}@example.com`;
  await page.goto("/sign-up");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
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

test("fresh judge completes the core sandbox journey", async ({ page }) => {
  await register(page, "judge-core");
  await expect(page.getByText("$1,000.00").first()).toBeVisible();

  await page.getByRole("link", { name: "Wallet" }).first().click();
  page.once("dialog", (dialog) => dialog.accept());
  await page.getByRole("button", { name: "$100.00" }).click();
  await expect(page.getByText("$1,100.00").first()).toBeVisible();

  await page.getByRole("link", { name: "New payment" }).first().click();
  await page.getByLabel("Vendor or recipient name").fill("Linear");
  await page.getByLabel("Amount (USD)").fill("49.00");
  await page.getByLabel("Category").selectOption("software");
  await page.getByLabel("Business reason").fill("Monthly software subscription");
  await submitPayment(page);
  await expect(page).toHaveURL(/\/app\/transactions\//);
  await expect(page.getByText("Completed").first()).toBeVisible();

  await page.getByRole("link", { name: "New payment" }).first().click();
  await page.getByRole("button", { name: "Payout" }).click();
  await page.getByLabel("Vendor or recipient name").fill("Ada Contractor");
  await page.getByLabel("Amount (USD)").fill("125.00");
  await page.getByLabel("Recipient email").fill("ada@example.com");
  await page.getByLabel("Category").selectOption("freelance");
  await page.getByLabel("Business reason").fill("Contract work");
  await submitPayment(page);
  await expect(page.getByText("Needs approval").first()).toBeVisible();

  await page.goto("/app/approvals");
  await expect(page.getByText("Ada Contractor")).toBeVisible();
  await page.getByRole("button", { name: "Approve" }).click();
  await expect(page.getByText("No requests need approval")).toBeVisible();

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
  await submitPayment(page);
  await expect(page.getByText("Needs approval").first()).toBeVisible();

  await page.goto("/app/payments/new?scenario=blocked");
  await submitPayment(page);
  await expect(page.getByText("Blocked").first()).toBeVisible();
  await expect(page.getByText("TRANSACTION_LIMIT_EXCEEDED", { exact: false })).toBeVisible();

  await page.goto("/app/payments/new?scenario=reject");
  await submitPayment(page);
  await page.goto("/app/approvals");
  const contractor = page.getByRole("article").filter({ hasText: "Contractor" });
  await contractor.getByRole("button", { name: "Reject" }).click();
  await contractor.getByLabel("Rejection reason for Contractor").fill("Invoice needs correction");
  await contractor.getByRole("button", { name: "Confirm rejection" }).click();
  await expect(contractor).not.toBeVisible();
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

test("transaction history recovers after a temporary API failure", async ({ page }) => {
  await register(page, "judge-recovery");
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
