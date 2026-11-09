import { expect, test, type Page } from "@playwright/test";
import { mkdirSync } from "node:fs";
import { fileURLToPath } from "node:url";

const demoEmail = "demo@pactra-demo.example.com";
const demoPassword = "PactraDemo2026!";
const assetDirectory = fileURLToPath(new URL("../../../DEMO/assets/", import.meta.url));

async function screenshot(page: Page, filename: string) {
  mkdirSync(assetDirectory, { recursive: true });
  await page.screenshot({
    path: `${assetDirectory}${filename}`,
    fullPage: true,
    animations: "disabled",
  });
}

async function expectNoHorizontalOverflow(page: Page) {
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
  expect(overflow).toBeLessThanOrEqual(1);
}

async function submitPayment(page: Page) {
  const submit = page.getByRole("button", {
    name: /Review request|Create payment request/,
  });
  await expect(submit).toBeVisible();
  await submit.click();
  const confirmation = page.getByRole("button", { name: "Confirm and create request" });
  const needsConfirmation = await confirmation
    .waitFor({ state: "visible", timeout: 1_500 })
    .then(() => true)
    .catch(() => false);
  if (needsConfirmation) await confirmation.click();
}

test("the isolated demo proves governance, fallback and auditability", async ({ page }) => {
  test.slow();
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/sign-in");
  await page.getByLabel("Email").fill(demoEmail);
  await page.getByLabel("Password", { exact: true }).fill(demoPassword);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page).toHaveURL(/\/app$/);
  await expect(page.getByText("$826.00").first()).toBeVisible();
  await expectNoHorizontalOverflow(page);
  await screenshot(page, "01-dashboard-desktop.png");

  await page.goto("/app/payments/new");
  await page.getByLabel("Vendor or recipient name").fill("Figma");
  await page.getByLabel("Amount (USD)").fill("35.00");
  await page.getByLabel("Category").selectOption("software");
  await page.getByLabel("Business reason").fill("Fictional design workspace subscription");
  await expect(page.getByText("Likely auto-approved")).toBeVisible();
  await screenshot(page, "02-governed-payment-review.png");
  await submitPayment(page);
  await expect(page).toHaveURL(/\/app\/transactions\//);
  await expect(page.getByText("Completed").first()).toBeVisible();
  await expect(page.getByText("Internal ledger capture")).toBeVisible();
  await screenshot(page, "03-completed-payment-receipt.png");

  await page.goto("/app/assistant");
  await page.getByLabel("Message Pactra").fill(
    "Pay Notion $20 for our software subscription",
  );
  await page.getByRole("button", { name: "Send message" }).click();
  await expect(
    page
      .locator(".assistant-message-assistant")
      .getByText(
        /Payment to Notion completed after backend policy and ledger confirmation/,
      ),
  ).toBeVisible();
  await page.getByLabel("Message Pactra").fill(
    "Pay Mega Cloud Renewal $200 for annual cloud hosting",
  );
  await page.getByRole("button", { name: "Send message" }).click();
  await expect(
    page
      .locator(".assistant-message-assistant")
      .getByText(/Policy blocked the payment request for Mega Cloud Renewal/),
  ).toBeVisible();
  await screenshot(page, "04-ai-governance-fallback.png");

  await page.setViewportSize({ width: 1024, height: 768 });
  await page.goto("/app/approvals");
  const pending = page.getByRole("article").filter({ hasText: "Ada Contractor" });
  await expect(pending.getByText("Needs approval")).toBeVisible();
  await expect(pending.getByText(demoEmail)).toHaveCSS("text-transform", "none");
  await expectNoHorizontalOverflow(page);
  await screenshot(page, "05-approval-tablet.png");
  await pending.getByRole("button", { name: "Approve" }).click();
  await expect(pending).not.toBeVisible();

  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/app/transactions?vendor=Ada%20Contractor");
  const adaGridCell = page.getByRole("gridcell", { name: "Ada Contractor" });
  await expect(adaGridCell).toBeVisible();
  await adaGridCell.click();
  await expect(page.getByRole("heading", { name: "Transaction receipt" })).toBeVisible();
  await expect(page.getByText("Completed").first()).toBeVisible();
  await expect(page.getByRole("heading", { name: "Lifecycle" })).toBeVisible();
  await screenshot(page, "06-approval-audit-receipt.png");

  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/app/transactions");
  await expect(page.getByRole("heading", { name: "Transactions" })).toBeVisible();
  await expect(page.getByText("Ada Contractor")).toBeVisible();
  await expectNoHorizontalOverflow(page);
  await screenshot(page, "07-transactions-mobile.png");
});
