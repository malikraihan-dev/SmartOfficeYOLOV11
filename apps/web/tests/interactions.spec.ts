import { test, expect } from "@playwright/test";

test.beforeEach(async ({ request, context }) => {
  await request.post("http://127.0.0.1:5051/test/control", { data: { populated: true } });
  await context.request.post("/api/auth/login", { headers: { "X-SmartOffice-Client": "web" }, data: { username: "admin", password: "test-admin-password-2026" } });
});

test("dashboard exposes device ages and requests selected chart period", async ({ page }) => {
  await page.goto("/monitoring");
  const status = page.getByRole("region", { name: "Status perangkat dan umur pembacaan" });
  await expect(status).toContainText("Sensor SCD40");
  await expect(status).toContainText("Belum ada pembacaan");
  const requested = page.waitForRequest(request => request.url().includes("/api/sensors/dataset?") && request.url().includes("period=24h"));
  await page.getByLabel("Periode grafik").selectOption("24h");
  expect(new URL((await requested).url()).searchParams.get("limit")).toBe("200");
  await page.getByRole("button", { name: "Jeda pembaruan", exact: true }).click();
  await expect(page.getByLabel("Periode grafik")).toBeDisabled();
});

test("dataset dates propagate to export and reset", async ({ page }) => {
  await page.goto("/datasets/sensors");
  await page.getByLabel("Dari tanggal").fill("2026-11-09");
  await page.getByLabel("Sampai tanggal").fill("2026-11-10");
  await page.getByRole("button", { name: "Terapkan tanggal" }).click();
  const download = page.getByRole("link", { name: "Unduh CSV asli", exact: true });
  await expect(download).toHaveAttribute("href", /from=.*to=/);
  await page.screenshot({ path: "../../docs/screenshots/sensor-date-filter.png", fullPage: true });
  const href = await download.getAttribute("href");
  const params = new URL(href!, "http://localhost").searchParams;
  expect(Date.parse(params.get("to")!) - Date.parse(params.get("from")!)).toBe(48 * 3600000);
  await page.getByRole("button", { name: "Reset tanggal" }).click();
  await expect(download).toHaveAttribute("href", "/api/sensors/export");
});

test("dataset image dialog closes with Escape and restores focus", async ({ page }) => {
  await page.goto("/datasets/vision");
  const trigger = page.getByRole("button", { name: "Pratinjau Sampel deteksi nomor 1", exact: true });
  await trigger.click();
  const dialog = page.getByRole("dialog", { name: "Sampel deteksi nomor 1", exact: true });
  await expect(dialog).toBeVisible();
  await expect(dialog.getByRole("button", { name: "Tutup gambar" })).toBeFocused();
  for (const width of [375, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    expect(await dialog.evaluate(element => element.scrollWidth <= element.clientWidth)).toBe(true);
    await page.screenshot({ path: `../../docs/screenshots/image-dialog-${width}.png` });
  }
  await page.keyboard.press("Escape");
  await expect(dialog).not.toBeVisible();
  await expect(trigger).toBeFocused();
});

test("failed audio save keeps unsaved marker and successful save clears it", async ({ page }) => {
  await page.goto("/settings");
  await expect(page.getByText("Pengaturan audio tersimpan", { exact: true })).toBeVisible();
  await page.getByLabel("Ambang audio").fill("-35");
  await page.route("**/api/audio/threshold", route => route.fulfill({ status: 500, contentType: "application/json", body: '{"message":"Gagal menyimpan"}' }));
  await page.getByRole("button", { name: "Simpan ambang", exact: true }).click();
  await expect(page.getByText("Gagal menyimpan", { exact: true })).toBeVisible();
  await expect(page.getByText("Perubahan audio belum disimpan", { exact: true })).toBeVisible();
  await page.screenshot({ path: "../../docs/screenshots/settings-unsaved.png", fullPage: true });
  await page.unroute("**/api/audio/threshold");
  await page.getByRole("button", { name: "Simpan ambang", exact: true }).click();
  await expect(page.getByText("Pengaturan audio tersimpan", { exact: true })).toBeVisible();
});
