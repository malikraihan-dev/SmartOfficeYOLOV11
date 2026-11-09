import { test, expect } from "@playwright/test";
test.beforeEach(async ({ request, context }) => {
  await request.post("http://127.0.0.1:5051/test/control", { data: {} });
  await context.request.post("/api/auth/login", { headers: { "X-SmartOffice-Client": "web" }, data: { username: "admin", password: "test-admin-password-2026" } });
});

test("approaching the rail expands it; leaving closes without moving content", async ({ page }) => {
  await page.goto("/monitoring");
  const sidebar = page.getByRole("complementary", { name: "Navigasi utama" });
  await page.mouse.move(600, 300);
  await expect(sidebar).toHaveAttribute("data-expanded", "false");
  const before = await page.locator(".main-shell").boundingBox();
  await page.mouse.move(100, 300);
  await expect(sidebar).toHaveAttribute("data-expanded", "true");
  await expect(sidebar.getByText("Dataset sensor", { exact: true })).toBeVisible();
  await expect(sidebar).toHaveCSS("width", "268px");
  const after = await page.locator(".main-shell").boundingBox();
  expect(after?.x).toBe(before?.x);
  await page.mouse.move(40, 250);
  await expect(sidebar.locator(".nav-copy").first()).toHaveCSS("opacity", "1");
  await page.screenshot({ path: "../../docs/screenshots/sidebar-expanded.png" });
  await expect(sidebar).toHaveAttribute("data-expanded", "true");
  await page.mouse.move(700, 300);
  await expect(sidebar).toHaveAttribute("data-expanded", "false");
  await expect(sidebar).toHaveCSS("width", "84px");
});

test("keyboard focus expands navigation and Escape collapses it", async ({ page }) => {
  await page.goto("/models");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Model & validasi");
  await page.mouse.move(700, 300);
  await page.keyboard.press("Tab");
  await page.getByRole("link", { name: "Dataset sensor", exact: true }).focus();
  const sidebar = page.getByRole("complementary", { name: "Navigasi utama" });
  await expect(sidebar).toHaveAttribute("data-expanded", "true");
  await page.keyboard.press("Escape");
  await expect(sidebar).toHaveAttribute("data-expanded", "false");
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/\/datasets\/sensors/);
});

test("mobile menu remains tap controlled and traps keyboard focus", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 900 });
  await page.goto("/monitoring");
  await page.getByRole("button", { name: "Buka menu" }).click();
  const menu = page.getByRole("dialog", { name: "Navigasi utama" });
  await expect(menu).toBeVisible();
  await expect(menu.getByRole("button", { name: "Tutup navigasi" })).toBeFocused();
  await page.keyboard.press("Shift+Tab");
  await expect(menu.getByRole("link", { name: "Pengaturan", exact: true })).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(menu.getByRole("button", { name: "Tutup navigasi" })).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("button", { name: "Buka menu" })).toBeFocused();
  await expect(menu).not.toBeVisible();
});
