import { expect, test } from "@playwright/test";

const acceptedPassword = "Aa1!aaaa";
const replacementPassword = "Bb2@bbbb";

test("the desktop product menu opens and closes from the keyboard", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");
  const productMenu = page.getByRole("button", { name: "Product" });
  await productMenu.focus();
  await productMenu.press("Enter");
  await expect(productMenu).toHaveAttribute("aria-expanded", "true");
  await expect(page.getByText("Policy controls", { exact: true }).first()).toBeVisible();
  await productMenu.press("Escape");
  await expect(productMenu).toHaveAttribute("aria-expanded", "false");
  await expect(productMenu).toBeFocused();
});

test("the mobile navigation closes with Escape and restores focus", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto("/");
  const navigationButton = page.getByRole("button", { name: "Open navigation" });
  await navigationButton.focus();
  await navigationButton.press("Enter");
  const closeButton = page.getByRole("button", { name: "Close navigation" });
  await expect(closeButton).toHaveAttribute("aria-expanded", "true");
  await page.locator("#public-mobile-navigation").getByRole("link", { name: "Sign in" }).press("Escape");
  await expect(page.getByRole("button", { name: "Open navigation" })).toBeFocused();
  await expect(page.locator("#public-mobile-navigation")).toHaveCount(0);
});

test("eight-character passwords work across registration, login, and password change", async ({ page }) => {
  const email = `password-boundary-${Date.now()}-${Math.random().toString(16).slice(2)}@example.com`;
  await page.goto("/sign-up");

  const signUpPassword = page.getByLabel("Password", { exact: true });
  await expect(signUpPassword).toHaveAttribute("minlength", "8");
  await expect(signUpPassword).toHaveAttribute("maxlength", "128");
  await expect(page.getByText("Use 8 to 128 characters")).toBeVisible();

  await page.getByLabel("Email").fill(email);
  await signUpPassword.fill("Aa1!aaa");
  expect(await signUpPassword.evaluate((input: HTMLInputElement) => input.checkValidity())).toBe(false);
  await page.getByRole("button", { name: "Create sandbox account" }).click();
  await expect(page).toHaveURL(/\/sign-up$/);

  await signUpPassword.fill(acceptedPassword);
  await page.getByRole("button", { name: "Create sandbox account" }).click();
  await expect(page).toHaveURL(/\/app$/);

  await page.goto("/app/settings");
  await page.getByRole("button", { name: "Sign out of this session" }).click();
  await expect(page).toHaveURL(/\/sign-in$/);
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password", { exact: true }).fill(acceptedPassword);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page).toHaveURL(/\/app$/);

  await page.goto("/app/settings");
  await expect(page.getByLabel("New password")).toHaveAttribute("minlength", "8");
  await page.getByLabel("Current password").fill(acceptedPassword);
  await page.getByLabel("New password").fill(replacementPassword);
  await page.getByRole("button", { name: "Change password" }).click();
  await expect(page.getByText("Password changed and other sessions revoked")).toBeVisible();

  await page.getByRole("button", { name: "Sign out of this session" }).click();
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password", { exact: true }).fill(acceptedPassword);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByText("Email or password is incorrect.")).toBeVisible();

  await page.getByLabel("Password", { exact: true }).fill(replacementPassword);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page).toHaveURL(/\/app$/);
});

test("public pages and footer remain complete across supported viewport widths", async ({ browser }) => {
  const routes = ["/", "/sign-in", "/sign-up", "/privacy", "/terms", "/missing-page"];
  const viewports = [
    { width: 320, height: 800 },
    { width: 375, height: 812 },
    { width: 768, height: 1024 },
    { width: 1024, height: 768 },
    { width: 1440, height: 1000 },
  ];

  for (const viewport of viewports) {
    const context = await browser.newContext({ viewport });
    const page = await context.newPage();
    const runtimeErrors: string[] = [];
    page.on("console", (message) => {
      if (message.type() === "error") runtimeErrors.push(message.text());
    });
    page.on("pageerror", (error) => runtimeErrors.push(error.message));

    for (const route of routes) {
      const response = await page.goto(route, { waitUntil: "domcontentloaded" });
      expect(response?.status(), `${route} at ${viewport.width}px`).toBe(200);
      await expect(page.locator("main")).toHaveCount(1);
      const footer = page.getByTestId("public-footer");
      await expect(footer).toBeVisible();
      await expect(footer.getByRole("link", { name: "Privacy policy" })).toBeVisible();
      await expect(footer.getByRole("link", { name: "Terms of use" })).toBeVisible();
      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
      );
      expect(overflow, `${route} horizontal overflow at ${viewport.width}px`).toBeLessThanOrEqual(1);
    }

    expect(runtimeErrors, `runtime errors at ${viewport.width}px`).toEqual([]);
    await context.close();
  }
});

test("authenticated routes remain responsive across supported viewport widths", async ({ browser }) => {
  test.setTimeout(120_000);
  const routes = [
    "/app",
    "/app/wallet",
    "/app/policies",
    "/app/payments/new",
    "/app/approvals",
    "/app/transactions",
    "/app/assistant",
    "/app/settings",
    "/app/settings/integrations/paypal",
    "/app/missing-page",
  ];
  const viewports = [
    { width: 320, height: 800 },
    { width: 375, height: 812 },
    { width: 768, height: 1024 },
    { width: 1024, height: 768 },
    { width: 1440, height: 1000 },
  ];

  for (const viewport of viewports) {
    const context = await browser.newContext({ viewport });
    const page = await context.newPage();
    const runtimeErrors: string[] = [];
    page.on("console", (message) => {
      if (message.type() === "error") runtimeErrors.push(message.text());
    });
    page.on("pageerror", (error) => runtimeErrors.push(error.message));

    await page.goto("/sign-up");
    await page.getByLabel("Email").fill(
      `responsive-${viewport.width}-${Date.now()}-${Math.random().toString(16).slice(2)}@example.com`,
    );
    await page.getByLabel("Password", { exact: true }).fill(acceptedPassword);
    await page.getByRole("button", { name: "Create sandbox account" }).click();
    await expect(page).toHaveURL(/\/app$/);

    for (const route of routes) {
      await page.goto(route);
      await expect(page.locator("main")).toBeVisible();
      await expect(page.locator(".loading-placeholder")).toHaveCount(0);
      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
      );
      expect(overflow, `${route} horizontal overflow at ${viewport.width}px`).toBeLessThanOrEqual(1);
    }

    expect(runtimeErrors, `runtime errors at ${viewport.width}px`).toEqual([]);
    await context.close();
  }
});
