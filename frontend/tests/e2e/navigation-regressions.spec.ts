import { expect, test, type Page } from "@playwright/test";

const password = "JudgePassword2026!";

async function register(page: Page, prefix: string) {
  const email = `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}@example.com`;
  await page.goto("/sign-up");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page).toHaveURL(/\/app$/);
  return email;
}

async function expectGuestHeader(page: Page) {
  const header = page.locator("header").first();
  await expect(header.getByRole("link", { name: "Sign in", exact: true })).toBeVisible();
  await expect(header.getByRole("link", { name: "Sign up", exact: true })).toBeVisible();
  await expect(header.getByRole("link", { name: "Dashboard", exact: true })).toHaveCount(0);
}

async function expectAuthenticatedHeader(page: Page) {
  const header = page.locator("header").first();
  await expect(header.getByRole("link", { name: "Dashboard", exact: true })).toBeVisible();
  await expect(header.getByRole("link", { name: "Sign in", exact: true })).toHaveCount(0);
  await expect(header.getByRole("link", { name: "Sign up", exact: true })).toHaveCount(0);
}

async function expectNoHorizontalOverflow(page: Page) {
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
  expect(overflow).toBeLessThanOrEqual(1);
}

test("guest navigation shows Sign in and Sign up on desktop and mobile", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");
  await expectGuestHeader(page);

  await page.locator("header").first().getByRole("link", { name: "Sign up", exact: true }).click();
  await expect(page).toHaveURL(/\/sign-up$/);
  await page.goBack();

  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole("button", { name: "Open navigation" }).click();
  const mobileNavigation = page.locator("#public-mobile-navigation");
  await expect(mobileNavigation.getByRole("link", { name: "Sign in", exact: true })).toBeVisible();
  await expect(mobileNavigation.getByRole("link", { name: "Sign up", exact: true })).toBeVisible();
  await mobileNavigation.getByRole("link", { name: "Sign up", exact: true }).click();
  await expect(page).toHaveURL(/\/sign-up$/);
});

test("authentication state survives refresh and stays synchronized across public and private routes", async ({ page }) => {
  await page.goto("/");
  await page.locator("header").first().getByRole("link", { name: "Sign up", exact: true }).click();
  const email = `auth-navigation-${Date.now()}-${Math.random().toString(16).slice(2)}@example.com`;
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page).toHaveURL(/\/app$/);

  await page.goBack();
  await expect(page).toHaveURL(/\/$/);
  await expectAuthenticatedHeader(page);
  await page.locator("header").first().getByRole("link", { name: "Dashboard", exact: true }).click();
  await expect(page).toHaveURL(/\/app$/);

  await page.goBack();
  await expectAuthenticatedHeader(page);
  await page.reload();
  await expectAuthenticatedHeader(page);

  await page.getByTestId("public-footer").getByRole("link", { name: "Privacy policy" }).click();
  await expectAuthenticatedHeader(page);
  await expect(page.getByRole("link", { name: "Sign in", exact: true })).toHaveCount(0);
  await expect(page.getByRole("link", { name: "Sign up", exact: true })).toHaveCount(0);
});

test("logout and an invalidated session return public navigation to guest state", async ({ page, context }) => {
  await register(page, "logout-navigation");
  await page.getByTestId("desktop-sidebar").getByRole("button", { name: "Sign out", exact: true }).click();
  await expect(page).toHaveURL(/\/sign-in$/);
  await page.goto("/");
  await expectGuestHeader(page);

  await register(page, "expired-navigation");
  const sessionCookie = (await context.cookies()).find((cookie) => cookie.name === "pactra_session");
  expect(sessionCookie).toBeDefined();
  await context.addCookies([{ ...sessionCookie!, value: "expired-session-fixture" }]);
  await page.goto("/");
  await expectGuestHeader(page);
  expect((await context.cookies()).some((cookie) => cookie.name === "pactra_session")).toBe(false);
});

test("session restoration never flashes guest actions and sends one request", async ({ page }) => {
  await register(page, "session-loading");
  let sessionRequests = 0;
  let releaseSession: (() => void) | undefined;
  const sessionReleased = new Promise<void>((resolve) => { releaseSession = resolve; });

  await page.route("**/api/auth/session", async (route) => {
    sessionRequests += 1;
    await sessionReleased;
    await route.continue();
  });

  await page.goto("/", { waitUntil: "domcontentloaded" });
  const header = page.locator("header").first();
  await expect(header.locator('[data-auth-state="loading"]')).toBeVisible();
  await expect(page.getByRole("link", { name: "Sign in", exact: true })).toHaveCount(0);
  await expect(page.getByRole("link", { name: "Sign up", exact: true })).toHaveCount(0);
  releaseSession?.();
  await expectAuthenticatedHeader(page);
  expect(sessionRequests).toBe(1);
});

test("a temporary session-check failure stays neutral and can recover", async ({ page }) => {
  await register(page, "session-error");
  await page.route("**/api/auth/session", (route) => route.fulfill({
    status: 503,
    contentType: "application/json",
    body: JSON.stringify({ error: { code: "SERVICE_UNAVAILABLE", message: "Temporary failure" } }),
  }));

  await page.goto("/");
  const header = page.locator("header").first();
  await expect(header.locator('[data-auth-state="error"]')).toBeVisible();
  await expect(page.getByRole("link", { name: "Sign in", exact: true })).toHaveCount(0);
  await expect(page.getByRole("link", { name: "Sign up", exact: true })).toHaveCount(0);

  await page.unroute("**/api/auth/session");
  await header.getByRole("button", { name: "Retry session" }).click();
  await expectAuthenticatedHeader(page);
});

test("desktop sidebar and main content keep independent scroll regions", async ({ page }) => {
  await register(page, "desktop-sidebar");
  await page.goto("/app/policies");

  for (const viewport of [
    { width: 1024, height: 768 },
    { width: 1280, height: 720 },
    { width: 1440, height: 900 },
    { width: 1919, height: 939 },
  ]) {
    await page.setViewportSize(viewport);
    const sidebar = page.getByTestId("desktop-sidebar");
    const footer = page.getByTestId("sidebar-footer");
    const mainScroll = page.getByTestId("main-content-scroll");

    await expect(sidebar).toBeVisible();
    await expect(footer.getByRole("button", { name: "Sign out", exact: true })).toBeVisible();
    for (const name of ["Overview", "Assistant", "New payment", "Approvals", "Transactions", "Policies", "Wallet", "Settings"]) {
      const link = sidebar.getByRole("link", { name, exact: true });
      await link.scrollIntoViewIfNeeded();
      await expect(link).toBeVisible();
    }

    const geometry = await page.evaluate(() => {
      const sidebarElement = document.querySelector<HTMLElement>('[data-testid="desktop-sidebar"]')!;
      const navigationElement = document.querySelector<HTMLElement>('[data-testid="sidebar-navigation-scroll"]')!;
      const footerElement = document.querySelector<HTMLElement>('[data-testid="sidebar-footer"]')!;
      const mainElement = document.querySelector<HTMLElement>('[data-testid="main-content-scroll"]')!;
      const sidebarRect = sidebarElement.getBoundingClientRect();
      const navigationRect = navigationElement.getBoundingClientRect();
      const footerRect = footerElement.getBoundingClientRect();
      const mainRect = mainElement.getBoundingClientRect();
      return {
        footerInsideViewport: footerRect.bottom <= innerHeight + 1,
        footerSeparatedFromNavigation: navigationRect.bottom <= footerRect.top + 1,
        mainStartsAfterSidebar: mainRect.left >= sidebarRect.right - 1,
        mainOverflowY: getComputedStyle(mainElement).overflowY,
        navigationOverflowY: getComputedStyle(navigationElement).overflowY,
        shellHeight: sidebarRect.height,
      };
    });
    expect(geometry.footerInsideViewport).toBe(true);
    expect(geometry.footerSeparatedFromNavigation).toBe(true);
    expect(geometry.mainStartsAfterSidebar).toBe(true);
    expect(geometry.mainOverflowY).toBe("auto");
    expect(geometry.navigationOverflowY).toBe("auto");
    expect(Math.abs(geometry.shellHeight - viewport.height)).toBeLessThanOrEqual(1);
    await expectNoHorizontalOverflow(page);

    const mainMetrics = await mainScroll.evaluate((element) => ({
      clientHeight: element.clientHeight,
      scrollHeight: element.scrollHeight,
    }));
    expect(mainMetrics.scrollHeight).toBeGreaterThan(mainMetrics.clientHeight);
    await mainScroll.evaluate((element) => element.scrollTo({ top: 160 }));
    expect(await mainScroll.evaluate((element) => element.scrollTop)).toBeGreaterThan(0);
    expect(await page.evaluate(() => window.scrollY)).toBe(0);
  }
});

test("short desktop heights keep the footer pinned while navigation scrolls", async ({ page }) => {
  await register(page, "short-sidebar");
  await page.setViewportSize({ width: 1280, height: 600 });
  const navigationScroll = page.getByTestId("sidebar-navigation-scroll");
  const footer = page.getByTestId("sidebar-footer");
  const mainScroll = page.getByTestId("main-content-scroll");
  const footerTopBefore = await footer.evaluate((element) => element.getBoundingClientRect().top);

  const metrics = await navigationScroll.evaluate((element) => ({
    clientHeight: element.clientHeight,
    scrollHeight: element.scrollHeight,
  }));
  expect(metrics.scrollHeight).toBeGreaterThan(metrics.clientHeight);
  await navigationScroll.evaluate((element) => element.scrollTo({ top: element.scrollHeight }));
  expect(await navigationScroll.evaluate((element) => element.scrollTop)).toBeGreaterThan(0);
  expect(await mainScroll.evaluate((element) => element.scrollTop)).toBe(0);
  expect(await footer.evaluate((element) => element.getBoundingClientRect().top)).toBe(footerTopBefore);
  await expect(footer.getByRole("button", { name: "Sign out", exact: true })).toBeVisible();
});

test("keyboard navigation reaches every desktop sidebar control after route changes", async ({ page }) => {
  await register(page, "keyboard-sidebar");
  await page.setViewportSize({ width: 1280, height: 600 });
  const sidebar = page.getByTestId("desktop-sidebar");
  const controls = [
    sidebar.getByRole("link", { name: "Overview", exact: true }),
    sidebar.getByRole("link", { name: "Assistant", exact: true }),
    sidebar.getByRole("link", { name: "New payment", exact: true }),
    sidebar.getByRole("link", { name: "Approvals", exact: true }),
    sidebar.getByRole("link", { name: "Transactions", exact: true }),
    sidebar.getByRole("link", { name: "Policies", exact: true }),
    sidebar.getByRole("link", { name: "Wallet", exact: true }),
    sidebar.getByRole("link", { name: "Settings", exact: true }),
    sidebar.getByRole("button", { name: "Sign out", exact: true }),
  ];

  await controls[0].focus();
  for (let index = 0; index < controls.length; index += 1) {
    await expect(controls[index]).toBeFocused();
    if (index < controls.length - 1) await page.keyboard.press("Tab");
  }

  await sidebar.getByRole("link", { name: "Wallet", exact: true }).click();
  await expect(page).toHaveURL(/\/app\/wallet$/);
  await expect(sidebar.getByRole("button", { name: "Sign out", exact: true })).toBeVisible();
});


test("mobile drawer keeps navigation and logout accessible at supported sizes", async ({ page }) => {
  await register(page, "mobile-sidebar");

  for (const viewport of [
    { width: 320, height: 700 },
    { width: 375, height: 812 },
    { width: 390, height: 844 },
    { width: 768, height: 1024 },
  ]) {
    await page.setViewportSize(viewport);
    await page.getByRole("button", { name: "Open navigation" }).click();
    const drawer = page.locator("#workspace-mobile-navigation");
    const navigationScroll = page.getByTestId("mobile-navigation-scroll");
    await expect(drawer).toBeVisible();
    expect(await navigationScroll.evaluate((element) => getComputedStyle(element).overflowY)).toBe("auto");
    for (const name of ["Overview", "Assistant", "New payment", "Approvals", "Transactions", "Policies", "Wallet", "Settings"]) {
      const link = drawer.getByRole("link", { name, exact: true });
      await link.scrollIntoViewIfNeeded();
      await expect(link).toBeVisible();
    }
    await expect(drawer.getByRole("button", { name: "Sign out", exact: true })).toBeVisible();
    await expectNoHorizontalOverflow(page);
    await drawer.getByRole("link", { name: "Wallet", exact: true }).click();
    await expect(page).toHaveURL(/\/app\/wallet$/);
    await expect(drawer).toHaveCount(0);
  }

  await page.setViewportSize({ width: 320, height: 560 });
  await page.getByRole("button", { name: "Open navigation" }).click();
  const shortNavigationScroll = page.getByTestId("mobile-navigation-scroll");
  const shortMetrics = await shortNavigationScroll.evaluate((element) => ({
    clientHeight: element.clientHeight,
    scrollHeight: element.scrollHeight,
  }));
  expect(shortMetrics.scrollHeight).toBeGreaterThan(shortMetrics.clientHeight);
  await shortNavigationScroll.evaluate((element) => element.scrollTo({ top: element.scrollHeight }));
  await expect(page.locator("#workspace-mobile-navigation").getByRole("button", { name: "Sign out", exact: true })).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.locator("#workspace-mobile-navigation")).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Open navigation" })).toBeFocused();
});
