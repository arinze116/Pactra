import { expect, test, type Page } from "@playwright/test";

const password = "RouteAuditPassword2026!";
const receiptScreenshot = "/home/ubuntu/pactra/artifacts/independent-audit-20261107/receipt-desktop.png";
const assistantResponseTimeoutMs = 60_000;

async function expectPageStable(page: Page, route: string) {
  const response = await page.goto(route, { waitUntil: "domcontentloaded" });
  expect(response?.status(), `${route} document status`).toBe(200);
  await expect(page.locator("body")).toBeVisible();
  await expect(page.locator(".loading-placeholder")).toHaveCount(0);
  const layout = await page.evaluate(() => ({
    overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
    brokenImages: Array.from(document.images)
      .filter((image) => image.complete && image.naturalWidth === 0)
      .map((image) => image.currentSrc || image.src),
  }));
  expect(layout.overflow, `${route} horizontal overflow`).toBeLessThanOrEqual(1);
  expect(layout.brokenImages, `${route} broken images`).toEqual([]);
}

async function submitScenarioPayment(page: Page) {
  await page.goto("/app/payments/new?scenario=auto");
  const submit = page.getByRole("button", { name: /Review request|Create payment request/ });
  if ((await submit.textContent())?.includes("Review")) {
    await submit.click();
    await page.getByRole("button", { name: "Confirm and create request" }).click();
  } else {
    await submit.click();
  }
  await expect(page).toHaveURL(/\/app\/transactions\/[a-f0-9-]+$/);
  return page.url();
}

async function createConversation(page: Page) {
  await page.goto("/app/assistant");
  await page.getByLabel("Message Pactra").fill("Please document this production route audit");
  await page.getByRole("button", { name: "Send message" }).click();
  await expect(page).toHaveURL(/\/app\/assistant\/[a-f0-9-]+$/);
  await expect(page.locator(".assistant-message-assistant")).toBeVisible({
    timeout: assistantResponseTimeoutMs,
  });
  return page.url();
}

test("all production routes reload without layout or runtime failures", async ({ browser }) => {
  for (const viewport of [
    { name: "desktop", width: 1440, height: 1000 },
    { name: "mobile", width: 390, height: 844 },
  ] as const) {
    const context = await browser.newContext({ viewport });
    const page = await context.newPage();
    const runtimeErrors: string[] = [];
    page.on("console", (message) => {
      if (message.type() === "error") runtimeErrors.push(message.text().slice(0, 500));
    });
    page.on("pageerror", (error) => runtimeErrors.push(error.message.slice(0, 500)));

    for (const route of ["/", "/sign-in", "/sign-up", "/privacy", "/terms", "/missing-page"]) {
      await expectPageStable(page, route);
      await page.reload({ waitUntil: "domcontentloaded" });
      await expectPageStable(page, route);
    }

    const email = `pactra-route-audit-${viewport.name}-${Date.now()}-${Math.random().toString(16).slice(2)}@example.com`;
    await page.goto("/sign-up");
    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Password", { exact: true }).fill(password);
    await page.getByRole("button", { name: "Create sandbox account" }).click();
    await expect(page).toHaveURL(/\/app$/);

    const receiptUrl = await submitScenarioPayment(page);
    const conversationUrl = await createConversation(page);
    const authenticatedRoutes = [
      "/app",
      "/app/payments/new",
      "/app/assistant",
      new URL(conversationUrl).pathname,
      "/app/approvals",
      "/app/transactions",
      new URL(receiptUrl).pathname,
      "/app/policies",
      "/app/wallet",
      "/app/settings",
      "/app/settings/integrations/paypal",
      "/app/missing-page",
    ];
    for (const route of authenticatedRoutes) {
      await expectPageStable(page, route);
      await page.reload({ waitUntil: "domcontentloaded" });
      await expectPageStable(page, route);
      await expect(page.locator("main")).toBeVisible();
      if (viewport.name === "desktop" && route === new URL(receiptUrl).pathname) {
        await page.screenshot({ path: receiptScreenshot, fullPage: true });
      }
    }

    expect(runtimeErrors, `${viewport.name} runtime errors`).toEqual([]);
    await context.close();
  }
});
