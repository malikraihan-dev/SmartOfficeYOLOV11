import { test, expect } from "@playwright/test";

test.beforeEach(async ({ request }) => { await request.post("http://127.0.0.1:5051/test/control", { data: {} }); });

test("anonymous requests redirect to login and cannot fetch protected data", async ({ page, request }) => {
  await page.goto("/monitoring");
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByRole("heading", { name: "Masuk ke ruang kendali." })).toBeVisible();
  for (const path of ["/api/status", "/api/sensors/export", "/video_feed", "/training_data/test.svg"]) {
    expect((await request.get(path)).status()).toBe(401);
  }
  await expect(page.getByText("Dashboard Flask", { exact: true })).toHaveCount(0);
  await expect(page.getByRole("navigation")).toHaveCount(0);
});

test("admin can log in, persist session across reload, and log out", async ({ page, context }) => {
  await page.goto("/login");
  await page.getByLabel("Nama pengguna", { exact: true }).fill("admin");
  await page.getByLabel("Kata sandi", { exact: true }).fill("test-admin-password-2026");
  await page.getByRole("button", { name: "Tampilkan kata sandi" }).click();
  await expect(page.getByLabel("Kata sandi", { exact: true })).toHaveAttribute("type", "text");
  await page.getByRole("button", { name: "Masuk ke dashboard" }).click();
  await expect(page).toHaveURL(/\/monitoring$/);
  const cookie = (await context.cookies()).find(item => item.name === "smartoffice_admin");
  expect(cookie?.httpOnly).toBe(true);
  expect(cookie?.sameSite).toBe("Lax");
  await page.reload();
  await expect(page.getByRole("heading", { name: "Monitoring ruang kerja" })).toBeVisible();
  await page.getByRole("button", { name: "Keluar dari akun admin" }).click();
  await expect(page).toHaveURL(/\/login$/);
  expect((await context.request.get("/api/status")).status()).toBe(401);
  await page.goto("/monitoring");
  await expect(page).toHaveURL(/\/login/);
});

test("invalid credentials keep the form with an accessible recovery message", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Nama pengguna", { exact: true }).fill("admin");
  await page.getByLabel("Kata sandi", { exact: true }).fill("wrong-password");
  await page.getByRole("button", { name: "Masuk ke dashboard" }).click();
  const error = page.getByRole("alert").filter({ hasText: "Nama pengguna atau kata sandi" });
  await expect(error).toBeVisible();
  await expect(error).toBeFocused();
  await expect(page.getByLabel("Nama pengguna", { exact: true })).toHaveValue("admin");
  await page.getByLabel("Kata sandi", { exact: true }).fill("test-admin-password-2026");
  await page.getByRole("button", { name: "Masuk ke dashboard" }).click();
  await expect(page).toHaveURL(/\/monitoring$/);
});

test("expired session redirects on the next protected request", async ({ page, context }) => {
  await context.request.post("/api/auth/login", { headers: { "X-SmartOffice-Client": "web" }, data: { username: "admin", password: "test-admin-password-2026" } });
  await page.goto("/monitoring");
  await expect(page.getByText("Simulasi · bukan data alat")).toHaveCount(3);
  await context.clearCookies();
  await expect(page).toHaveURL(/\/login\?reason=session/, { timeout: 12000 });
});

test("login fits mobile and desktop without polling camera or status", async ({ page, request }) => {
  for (const width of [320, 375, 768, 1440]) {
    await page.setViewportSize({ width, height: 960 });
    await page.goto("/login");
    await expect(page.getByRole("button", { name: "Masuk ke dashboard" })).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    if (width === 375 || width === 1440) await page.screenshot({ path: `../../docs/screenshots/login-${width}.png`, fullPage: true });
  }
  const calls = await (await request.get("http://127.0.0.1:5051/test/calls")).json();
  expect(calls.some((call: { path: string }) => call.path === "/api/status")).toBe(false);
});
