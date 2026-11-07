import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

const password = "JudgePassword2026!";

test.use({ reducedMotion: "reduce" });

async function expectWcag21AA(page: Page, label: string) {
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    .analyze();
  const violations = results.violations.map((violation) => ({
    id: violation.id,
    impact: violation.impact,
    help: violation.help,
    targets: violation.nodes.map((node) => node.target),
  }));
  expect(violations, `${label} accessibility violations`).toEqual([]);
}

async function expectAuthenticatedPageAccessible(page: Page, label: string) {
  await expect(page.locator("main")).toBeVisible();
  await expect(page.locator(".loading-placeholder")).toHaveCount(0);
  await expectWcag21AA(page, label);
}

async function register(page: Page) {
  const email = `judge-a11y-${Date.now()}-${Math.random().toString(16).slice(2)}@example.com`;
  await page.goto("/sign-up");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Create sandbox account" }).click();
  await expect(page).toHaveURL(/\/app$/);
}

test("public and authenticated judge surfaces meet automated WCAG 2.1 AA checks", async ({ page }) => {
  test.setTimeout(60_000);
  const publicRoutes = [
    ["/", "Landing page"],
    ["/sign-in", "Sign-in page"],
    ["/sign-up", "Registration page"],
    ["/missing-page", "Public not-found page"],
  ] as const;

  for (const [route, label] of publicRoutes) {
    await page.goto(route);
    await expectWcag21AA(page, label);
  }

  await register(page);
  await expectAuthenticatedPageAccessible(page, "Overview page");

  const routes = [
    ["/app/wallet", "Wallet page"],
    ["/app/policies", "Policy page"],
    ["/app/payments/new", "New payment page"],
    ["/app/approvals", "Approvals page"],
    ["/app/transactions", "Transactions page"],
    ["/app/assistant", "Assistant page"],
    ["/app/settings", "Settings page"],
    ["/app/settings/integrations/paypal", "PayPal integration page"],
    ["/app/missing-page", "Authenticated not-found page"],
  ] as const;

  for (const [route, label] of routes) {
    await page.goto(route);
    await expectAuthenticatedPageAccessible(page, label);
  }
});
