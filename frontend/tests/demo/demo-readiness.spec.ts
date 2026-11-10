import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Browser, type Page } from "@playwright/test";
import { mkdirSync } from "node:fs";
import { fileURLToPath } from "node:url";

const demoBanner = "DEMO WORKSPACE · SANDBOX FUNDS ONLY · NO REAL MONEY MOVES";
const screenshotDirectory = fileURLToPath(
  new URL("../../../QA/DEMO/screenshots/", import.meta.url),
);

interface DemoEntry {
  elapsedMs: number;
  userId: string;
}

async function enterDemo(page: Page, verifyLoadingState = false): Promise<DemoEntry> {
  await page.goto("/");
  await expect(page.locator('[data-auth-state="unauthenticated"]').first()).toBeVisible();
  await expect(
    page.getByText("Explore Pactra's payment governance workspace. No account required."),
  ).toBeVisible();

  if (verifyLoadingState) {
    await page.route("**/api/demo/sessions", async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 200));
      await route.continue();
    }, { times: 1 });
  }

  const button = page.getByTestId("explore-demo-primary");
  const responsePromise = page.waitForResponse((response) => {
    const url = new URL(response.url());
    return url.pathname === "/api/demo/sessions" && response.request().method() === "POST";
  });
  const startedAt = Date.now();
  await button.click();
  if (verifyLoadingState) await expect(button).toHaveText("Preparing demo…");
  const response = await responsePromise;
  expect(response.status()).toBe(201);
  const body = await response.json() as { user: { id: string; is_demo: boolean } };
  expect(body.user.is_demo).toBe(true);

  await expect(page).toHaveURL(/\/app$/);
  await expect(page.getByText(demoBanner, { exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Payment operations" })).toBeVisible();
  return { elapsedMs: Date.now() - startedAt, userId: body.user.id };
}

async function expectSeededDashboard(page: Page) {
  await expect(page.getByText("$825.00", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("$140.00", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("$965.00", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("Frame.io", { exact: true })).toBeVisible();
  await expect(page.getByText("Northstar Print House", { exact: true })).toBeVisible();
  await expect(page.getByText("Restricted Supply Co", { exact: true })).toBeVisible();
}

async function expectFreshWalkthrough(page: Page) {
  await expect(page.getByText("Judge walkthrough", { exact: true })).toBeVisible();
  await expect(page.getByText("0/7", { exact: true })).toBeVisible();
}

async function submitPayment(page: Page) {
  const submit = page.getByRole("button", {
    name: /Review request|Create payment request/,
  });
  await expect(submit).toBeEnabled();
  await submit.click();
  const confirmation = page.getByRole("button", {
    name: "Confirm and create request",
  });
  if (await confirmation.isVisible()) await confirmation.click();
}

async function expectNoHorizontalOverflow(page: Page) {
  const overflow = await page.evaluate(() => {
    const main = document.querySelector<HTMLElement>('[data-testid="main-content-scroll"]');
    return {
      document: document.documentElement.scrollWidth - document.documentElement.clientWidth,
      main: main ? main.scrollWidth - main.clientWidth : 0,
    };
  });
  expect(overflow.document).toBeLessThanOrEqual(1);
  expect(overflow.main).toBeLessThanOrEqual(1);
}

async function expectWcag21AA(page: Page, label: string) {
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    .analyze();
  expect(
    results.violations.map((violation) => ({
      id: violation.id,
      impact: violation.impact,
      targets: violation.nodes.map((node) => node.target),
    })),
    `${label} accessibility violations`,
  ).toEqual([]);
}

async function createTwoDemoPages(browser: Browser) {
  const firstContext = await browser.newContext();
  const secondContext = await browser.newContext();
  return {
    firstContext,
    firstPage: await firstContext.newPage(),
    secondContext,
    secondPage: await secondContext.newPage(),
  };
}

test("fresh judges enter isolated demos and complete the critical governance journey", async ({ browser }) => {
  test.setTimeout(120_000);
  const { firstContext, firstPage, secondContext, secondPage } = await createTwoDemoPages(browser);
  try {
    const [firstDemo, secondDemo] = await Promise.all([
      enterDemo(firstPage, true),
      enterDemo(secondPage),
    ]);
    expect(firstDemo.userId).not.toBe(secondDemo.userId);
    expect(firstDemo.elapsedMs).toBeLessThan(3_000);
    expect(secondDemo.elapsedMs).toBeLessThan(3_000);
    await expectSeededDashboard(firstPage);
    await expectSeededDashboard(secondPage);
    await expectFreshWalkthrough(firstPage);

    await firstPage.reload();
    await expect(firstPage.getByText(demoBanner, { exact: true })).toBeVisible();
    await expectSeededDashboard(firstPage);

    await firstPage.goto("/app/policies");
    await expect(firstPage.getByRole("heading", { name: "Spending policy" })).toBeVisible();
    await expect(firstPage.getByLabel("Daily limit")).toHaveValue("500.00");
    await expect(firstPage.getByLabel("Per transaction")).toHaveValue("750.00");
    await expect(firstPage.getByLabel("Approval above")).toHaveValue("100.00");
    await expect(firstPage.getByLabel("Blocked vendors")).toHaveValue("Restricted Supply Co");

    await firstPage.goto("/app/payments/new?scenario=auto");
    await expect(firstPage.getByText("Likely auto-approved")).toBeVisible();
    await submitPayment(firstPage);
    await expect(firstPage.getByRole("heading", { name: "Transaction receipt" })).toBeVisible();
    await expect(firstPage.getByText("Completed", { exact: true }).first()).toBeVisible();
    await expect(firstPage.getByText("Internal ledger capture", { exact: true })).toBeVisible();

    await secondPage.goto("/app/transactions");
    await expect(secondPage.getByRole("heading", { name: "Transactions" })).toBeVisible();
    await expect(secondPage.getByText("Linear", { exact: true })).toHaveCount(0);

    await firstPage.goto("/app/payments/new?scenario=approval");
    await expect(firstPage.getByText("Likely needs approval")).toBeVisible();
    await submitPayment(firstPage);
    await expect(firstPage.getByText("Needs approval", { exact: true }).first()).toBeVisible();
    const approvalReceiptUrl = firstPage.url();

    await firstPage.goto("/app/approvals");
    const approval = firstPage.getByRole("article").filter({ hasText: "Figma Teams" });
    await expect(approval.getByText("$120.00", { exact: true })).toBeVisible();
    await expect(approval.getByText("Northstar Studio", { exact: true })).toBeVisible();
    await expect(approval.getByText(/approval required/i).first()).toBeVisible();
    await approval.getByRole("button", { name: "Approve" }).click();
    await expect(approval).not.toBeVisible();

    await firstPage.goto(approvalReceiptUrl);
    await expect(firstPage.getByText("Completed", { exact: true }).first()).toBeVisible();
    await expect(firstPage.getByRole("heading", { name: "Lifecycle" })).toBeVisible();
    await expect(firstPage.getByRole("heading", { name: "Ledger impact" })).toBeVisible();
    await expect(firstPage.getByText(/Demo receipt · simulated internal sandbox evidence/)).toBeVisible();

    await firstPage.goto("/app/payments/new?scenario=blocked");
    await expect(firstPage.getByText("Likely blocked")).toBeVisible();
    await submitPayment(firstPage);
    await expect(firstPage.getByText("Blocked", { exact: true }).first()).toBeVisible();
    await expect(firstPage.getByText(/vendor blocked/i)).toBeVisible();

    const firstBanner = firstPage.locator(".demo-banner");
    await firstBanner.getByRole("button", { name: "Reset demo", exact: true }).click();
    const resetDialog = firstPage.getByRole("dialog", { name: "Reset demo workspace?" });
    await expect(resetDialog).toBeVisible();
    await resetDialog.getByRole("button", { name: "Reset demo", exact: true }).click();
    await expect(firstPage).toHaveURL(/\/app$/);
    await expectSeededDashboard(firstPage);
    await expectFreshWalkthrough(firstPage);
    await firstPage.goto("/app/transactions");
    await expect(firstPage.getByText("Linear", { exact: true })).toHaveCount(0);
    await expect(firstPage.getByText("Figma Teams", { exact: true })).toHaveCount(0);

    await firstBanner.getByRole("button", { name: "Exit demo", exact: true }).click();
    const exitDialog = firstPage.getByRole("dialog", { name: "Exit demo mode?" });
    await exitDialog.getByRole("button", { name: "Exit demo", exact: true }).click();
    await expect(firstPage).toHaveURL((url) => url.pathname === "/");
    await expect(firstPage.locator('[data-auth-state="unauthenticated"]').first()).toBeVisible();
    await expect(firstPage.getByRole("button", { name: "Explore demo", exact: true }).first()).toBeVisible();
    await expect(firstPage.getByRole("link", { name: "Sign up", exact: true }).first()).toBeVisible();
    await expect(firstPage.getByRole("link", { name: "Sign in", exact: true }).first()).toBeVisible();
  } finally {
    await firstContext.close();
    await secondContext.close();
  }
});

test("instant demo is responsive and keeps reset, exit, navigation, and content reachable", async ({ page }) => {
  test.setTimeout(90_000);
  await enterDemo(page);
  mkdirSync(screenshotDirectory, { recursive: true });
  const viewports = [
    { width: 320, height: 700 },
    { width: 375, height: 812 },
    { width: 390, height: 844 },
    { width: 768, height: 1024 },
    { width: 1280, height: 720 },
    { width: 1440, height: 900 },
    { width: 1919, height: 939 },
  ];

  for (const viewport of viewports) {
    await page.setViewportSize(viewport);
    await page.goto("/app");
    await expect(page.getByText(demoBanner, { exact: true })).toBeVisible();
    const banner = page.locator(".demo-banner");
    await expect(banner.getByRole("button", { name: "Reset demo", exact: true })).toBeVisible();
    await expect(banner.getByRole("button", { name: "Exit demo", exact: true })).toBeVisible();
    await expectNoHorizontalOverflow(page);
    await page.screenshot({
      animations: "disabled",
      path: `${screenshotDirectory}dashboard-${viewport.width}x${viewport.height}.png`,
    });

    if (viewport.width < 1024) {
      await page.getByRole("button", { name: "Open navigation" }).click();
      await expect(page.getByTestId("mobile-navigation-scroll")).toBeVisible();
      await expect(page.getByTestId("sidebar-footer").getByRole("button", { name: "Exit demo" })).toBeVisible();
      await page.getByRole("button", { name: "Close navigation" }).click();
    } else {
      await expect(page.getByTestId("desktop-sidebar")).toBeVisible();
      await expect(page.getByTestId("sidebar-navigation-scroll")).toBeVisible();
      await expect(page.getByTestId("sidebar-footer")).toBeVisible();
    }
  }
});

test("demo landing, dashboard, and confirmation dialog meet automated WCAG checks", async ({ page }) => {
  test.setTimeout(60_000);
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/");
  await expect(page.locator('[data-auth-state="unauthenticated"]').first()).toBeVisible();
  await expectWcag21AA(page, "Instant-demo landing page");

  await enterDemo(page);
  await expect(page.locator(".loading-placeholder")).toHaveCount(0);
  await expectWcag21AA(page, "Instant-demo dashboard");

  const resetButton = page.locator(".demo-banner").getByRole("button", { name: "Reset demo", exact: true });
  await resetButton.focus();
  await page.keyboard.press("Enter");
  const dialog = page.getByRole("dialog", { name: "Reset demo workspace?" });
  await expect(dialog).toBeVisible();
  await expect(dialog.getByRole("button", { name: "Cancel" })).toBeFocused();
  await expectWcag21AA(page, "Instant-demo reset dialog");
  await page.keyboard.press("Escape");
  await expect(dialog).not.toBeVisible();
});

test("normal registration, sign-out, and sign-in remain functional", async ({ page }) => {
  const email = `instant-demo-regression-${Date.now()}@example.com`;
  const password = "InstantDemoRegression2026!";
  await page.goto("/sign-up");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page).toHaveURL(/\/app$/);
  await expect(page.getByText(demoBanner, { exact: true })).toHaveCount(0);

  await page.getByTestId("sidebar-footer").getByRole("button", { name: "Sign out" }).click();
  await expect(page).toHaveURL(/\/sign-in$/);
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page).toHaveURL(/\/app$/);
  await expect(page.getByText(demoBanner, { exact: true })).toHaveCount(0);
});
