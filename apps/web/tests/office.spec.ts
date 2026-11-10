import { test, expect } from "@playwright/test";
test.beforeEach(async ({ request, context }) => {
  await request.post("http://127.0.0.1:5051/test/control", { data: {} });
  const response = await context.request.post("http://127.0.0.1:3100/api/auth/login", { headers: { "X-SmartOffice-Client": "web" }, data: { username: "admin", password: "test-admin-password-2026" } });
  expect(response.ok()).toBe(true);
});
test("monitoring labels demo and hides unavailable camera counts", async ({ page }) => {
  await page.goto("/monitoring");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Monitoring ruang kerja");
  await expect(page.getByText("DEMO", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("Simulasi · bukan data alat")).toHaveCount(3);
  await page.getByRole("button", { name: "Jeda pembaruan" }).click();
  await expect(page.getByText("DIJEDA", { exact: true }).first()).toBeVisible();
});
test("empty sensor dataset blocks real export and does not fabricate predictions", async ({ page }) => {
  await page.goto("/datasets/sensors");
  await expect(page.getByRole("heading", { name: "Belum ada pembacaan sensor" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Unduh CSV asli", exact: true })).toBeDisabled();
  await expect(page.getByText("MODEL BELUM DIHUBUNGKAN", { exact: true })).toBeVisible();
});
test("populated sensor table has 12 real rows and export works through proxy", async ({ page, request }) => {
  await request.post("http://127.0.0.1:5051/test/control", { data: { populated: true } });
  await page.goto("/datasets/sensors");
  await expect(page.locator("tbody tr")).toHaveCount(12);
  await page.screenshot({ path: "../../docs/screenshots/sensor-dataset-populated.png", fullPage: true });
  const download = page.waitForEvent("download");
  await page.getByRole("link", { name: "Unduh CSV asli", exact: true }).click();
  expect((await download).suggestedFilename()).toBe("test.csv");
});
test("offline is explicit and retry recovers without inventing data", async ({ page, request }) => {
  await request.post("http://127.0.0.1:5051/test/control", { data: { offline: true } });
  await page.goto("/datasets/sensors");
  await expect(page.getByText("Koneksi server terputus")).toBeVisible();
  await expect(page.getByRole("button", { name: "Unduh CSV asli", exact: true })).toBeDisabled();
  await request.post("http://127.0.0.1:5051/test/control", { data: { populated: true } });
  await page.getByRole("button", { name: "Coba lagi", exact: true }).click();
  await expect(page.locator("tbody tr")).toHaveCount(12);
  await expect(page.getByText("Koneksi server terputus")).toHaveCount(0);
});
test("stale sensor readings never receive a live badge", async ({ page, request }) => {
  await request.post("http://127.0.0.1:5051/test/control", { data: { live: true, stale: true } });
  await page.goto("/monitoring");
  await expect(page.getByText("KEDALUWARSA", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("Pembacaan SCD40 terbaru", { exact: true })).toHaveCount(0);
});
test("camera controls use existing Flask endpoints", async ({ page, request }) => {
  await request.post("http://127.0.0.1:5051/test/control", { data: { live: true } });
  await page.goto("/monitoring");
  await expect(page.getByRole("button", { name: "Ambil snapshot", exact: true })).toBeEnabled();
  await page.getByRole("button", { name: "Ambil snapshot", exact: true }).click();
  await expect(page.getByText("Snapshot berhasil disimpan.")).toBeVisible();
  await page.getByRole("button", { name: "Jeda pratinjau kamera" }).click();
  await expect(page.locator('img[src^="/video_feed"]')).toHaveCount(0);
  const calls = await (await request.get("http://127.0.0.1:5051/test/calls")).json();
  expect(calls.some((call: { path: string }) => call.path === "/api/snapshot")).toBe(true);
});
test("settings preserve edits during polling and submit normalized zone", async ({ page, request }) => {
  await page.goto("/settings");
  const save = page.getByRole("button", { name: "Terapkan pengaturan" });
  await expect(save).toBeEnabled();
  await page.getByLabel("Ambang confidence").fill("50");
  await expect(page.getByText("Perubahan deteksi belum disimpan", { exact: true })).toBeVisible();
  await page.waitForTimeout(4300);
  await expect(page.getByLabel("Ambang confidence")).toHaveValue("50");
  await save.click();
  await expect(page.getByText("Perubahan berhasil disimpan.")).toBeVisible();
  await expect(page.getByText("Pengaturan deteksi tersimpan", { exact: true })).toBeVisible();
  const calls = await (await request.get("http://127.0.0.1:5051/test/calls")).json();
  expect(calls.find((call: { path: string }) => call.path === "/api/detection/settings").body).toEqual({ confidence: .5, zone: { x1: .12, y1: .15, x2: .88, y2: .92 } });
});
test("invalid zone is blocked before mutation", async ({ page }) => {
  await page.goto("/settings");
  await expect(page.getByRole("button", { name: "Terapkan pengaturan" })).toBeEnabled();
  await page.getByLabel("Batas kiri").fill("90");
  await page.getByRole("button", { name: "Terapkan pengaturan" }).click();
  await expect(page.getByRole("alert").filter({ hasText: "Lebar dan tinggi zona" })).toContainText("Lebar dan tinggi zona harus minimal 10%");
});
test("deletion requires explicit typed confirmation and supports keyboard cancel", async ({ page, request }) => {
  await page.goto("/settings");
  const trigger = page.getByRole("button", { name: "Hapus data kamera & audio", exact: true });
  await trigger.click();
  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  await expect(dialog.getByRole("button", { name: "Hapus permanen" })).toBeDisabled();
  await page.keyboard.press("Escape");
  await expect(dialog).not.toBeVisible();
  await expect(trigger).toBeFocused();
  const calls = await (await request.get("http://127.0.0.1:5051/test/calls")).json();
  expect(calls.some((call: { path: string }) => call.path === "/api/data/clear")).toBe(false);
});
test("vision review and audio labels post to the correct sample", async ({ page, request }) => {
  await request.post("http://127.0.0.1:5051/test/control", { data: { populated: true } });
  await page.goto("/datasets/vision");
  await page.getByLabel("Jumlah aktual").fill("3");
  await page.getByRole("button", { name: "Konfirmasi", exact: true }).click();
  await expect(page.getByText("Ulasan tersimpan.")).toBeVisible();
  await page.goto("/settings");
  await page.getByRole("button", { name: "Tandai sampel audio 1 sebagai Hening" }).click();
  await expect(page.getByText("Label audio tersimpan.")).toBeVisible();
  const calls = await (await request.get("http://127.0.0.1:5051/test/calls")).json();
  expect(calls.find((call: { path: string }) => call.path === "/api/evaluation/1/review").body).toEqual({ actual_count: 3 });
  expect(calls.find((call: { path: string }) => call.path === "/api/audio/review/1").body).toEqual({ actual_label: "quiet" });
});
test("all routes fit narrow screens and navigation works with keyboard", async ({ page }) => {
  test.setTimeout(90000);
  const runtimeErrors: string[] = [];
  page.on("pageerror", error => runtimeErrors.push(error.message));
  const titles: Record<string, string> = {
    "/monitoring": "Monitoring ruang kerja", "/datasets/sensors": "Dataset sensor",
    "/datasets/vision": "Dataset kamera", "/models": "Model & validasi", "/settings": "Pengaturan ruang kerja",
  };
  for (const width of [320, 375, 768, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    for (const path of ["/monitoring", "/datasets/sensors", "/datasets/vision", "/models", "/settings"]) {
      await page.goto(path);
      await expect(page.getByRole("heading", { level: 1 })).toHaveText(titles[path]);
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
      if ((width === 375 || width === 1440) && (path === "/monitoring" || path === "/datasets/sensors")) {
        if (width > 760) {
          await page.mouse.move(700, 350);
          await expect(page.getByRole("complementary", { name: "Navigasi utama" })).toHaveCSS("width", "84px");
        }
        await page.screenshot({ path: `../../docs/screenshots/${path === "/monitoring" ? "monitoring" : "sensor-dataset"}-${width}.png`, fullPage: true, animations: "disabled" });
      }
    }
  }
  await page.setViewportSize({ width: 375, height: 900 });
  await page.getByRole("button", { name: "Buka menu" }).click();
  await page.getByRole("link", { name: "Dataset sensor", exact: true }).focus();
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/\/datasets\/sensors/);
  expect(runtimeErrors).toEqual([]);
});
