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
  await page.getByPlaceholder("Enter a payment or wallet request").fill("Pay Notion $20 for our software subscription");
  await page.getByRole("button", { name: "Send message" }).click();
  await expect(page.getByText(/Payment request created for Notion/)).toBeVisible();
  await expect(page.getByRole("link", { name: "Open transaction receipt" })).toBeVisible();

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
  await expect(page.getByText("Policy saved")).toBeVisible();
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
      shouldFail = false;
      await route.abort("failed");
      return;
    }
    await route.continue();
  });
  await page.goto("/app/transactions");
  await expect(page.getByText("Failed to fetch")).toBeVisible();
  await page.getByRole("button", { name: "Try again" }).click();
  await expect(page.getByText("No matching transactions")).toBeVisible();
});
