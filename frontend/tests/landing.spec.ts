import { test, expect } from "@playwright/test";

test.beforeEach(async ({ request }) => { await request.post("http://127.0.0.1:5051/test/control", { data: {} }); });

test("public landing shows features, honest pricing and a labeled interactive preview", async ({ page, request }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Ruang kerja cerdas.");
  await expect(page.getByText("DEMO · ILUSTRASI", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Suhu", exact: true }).click();
  await expect(page.getByRole("img", { name: /Suhu ruangan, data ilustrasi/ })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Data ruang, dari setiap sisi." })).toBeVisible();
  await expect(page.getByText("Harga belum ditetapkan", { exact: true })).toBeVisible();
  await expect(page.getByText("Belum ada langganan, checkout, atau pembayaran yang diaktifkan pada aplikasi ini.")).toBeVisible();
  const calls = await (await request.get("http://127.0.0.1:5051/test/calls")).json();
  expect(calls).toEqual([]);
  await page.getByRole("link", { name: "Buka ruang kendali" }).click();
  await expect(page).toHaveURL(/\/login$/);
});

test("landing, login and public navigation work at narrow widths with reduced motion", async ({ page }) => {
  test.setTimeout(60000);
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  await page.emulateMedia({ reducedMotion: "reduce" });
  for (const width of [320, 375, 768, 1440]) {
    await page.setViewportSize({ width, height: 960 });
    await page.goto("/");
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    if (width === 375 || width === 1440) await page.screenshot({ path: `../../docs/screenshots/landing-${width}.png`, fullPage: true, animations: "disabled" });
  }
  await page.setViewportSize({ width: 375, height: 960 });
  const menu = page.getByRole("button", { name: "Buka navigasi situs" });
  await menu.click();
  await expect(page.getByRole("navigation", { name: "Navigasi situs" })).toBeVisible();
  await page.getByRole("link", { name: "Harga", exact: true }).click();
  await expect(page).toHaveURL(/\/#harga$/);
  await expect(menu).toHaveAttribute("aria-expanded", "false");
  await menu.click();
  await page.keyboard.press("Escape");
  await expect(menu).toBeFocused();
  await expect(menu).toHaveAttribute("aria-expanded", "false");
  expect(errors).toEqual([]);
});

test("monitoring chart uses stored sensor values and preserves unavailable states", async ({ page, context, request }) => {
  await context.request.post("/api/auth/login", { headers: { "X-SmartOffice-Client": "web" }, data: { username: "admin", password: "test-admin-password-2026" } });
  await request.post("http://127.0.0.1:5051/test/control", { data: { populated: true, live: true } });
  await page.goto("/monitoring");
  await expect(page.getByRole("img", { name: /Riwayat CO₂, data tersimpan/ })).toHaveAttribute("aria-label", /731 ppm.*720 ppm/);
  await expect(page.getByText("12 pembacaan tersimpan", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Suhu", exact: true }).click();
  await expect(page.getByRole("img", { name: /Riwayat suhu, data tersimpan/ })).toHaveAttribute("aria-label", /25,4 °C/);
  await page.getByRole("button", { name: "Jeda pembaruan" }).click();
  await expect(page.getByRole("button", { name: "Perbarui grafik sensor" })).toBeDisabled();
  await request.post("http://127.0.0.1:5051/test/control", { data: {} });
  await page.getByRole("button", { name: "Lanjutkan pembaruan" }).click();
  await expect(page.getByText("Belum ada riwayat asli", { exact: true })).toBeVisible();
  await expect(page.getByRole("img", { name: /Riwayat suhu, data tersimpan/ })).toHaveAttribute("aria-label", /Belum ada riwayat/);
});
