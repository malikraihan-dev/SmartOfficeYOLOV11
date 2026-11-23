import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, existsSync, readFileSync, readdirSync, unlinkSync, rmdirSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { createServer } from "node:net";
import { setTimeout as delay } from "node:timers/promises";
import { runServices, ensurePortFree } from "./dev.mjs";

async function waitFor(check) {
  for (let i = 0; i < 100; i++) { if (check()) return; await delay(50); }
  throw new Error("Proses uji tidak mencapai keadaan yang diharapkan.");
}
const alive = pid => { try { process.kill(pid, 0); return true; } catch { return false; } };

test("stopping the launcher terminates its children and descendants", { timeout: 15000 }, async t => {
  const folder = mkdtempSync(join(tmpdir(), "smartoffice-launcher-"));
  const pidFile = join(folder, "descendant.pid");
  const script = "const {spawn}=require('node:child_process'); const {writeFileSync}=require('node:fs'); const child=spawn(process.execPath,['-e','setInterval(()=>{},1000)'],{windowsHide:true,stdio:'ignore'}); writeFileSync(process.argv[1],String(child.pid)); setInterval(()=>{},1000);";
  const services = runServices([{ name: "fixture", command: process.execPath, args: ["-e", script, pidFile] }], { stdio: "ignore" });
  t.after(async () => { await services.stop(); for (const name of readdirSync(folder)) unlinkSync(join(folder, name)); rmdirSync(folder); });
  await waitFor(() => existsSync(pidFile));
  const descendant = Number(readFileSync(pidFile, "utf8"));
  assert.equal(alive(descendant), true);
  await services.stop();
  assert.equal(await services.done, 0);
  await waitFor(() => !alive(descendant));
  assert.equal(services.children[0].exitCode !== null || services.children[0].signalCode !== null, true);
});

test("a failing service stops the other service and preserves failure status", { timeout: 15000 }, async t => {
  const services = runServices([
    { name: "waiting", command: process.execPath, args: ["-e", "setInterval(()=>{},1000)"] },
    { name: "failure", command: process.execPath, args: ["-e", "process.exit(23)"] },
  ], { stdio: "ignore" });
  t.after(() => services.stop());
  assert.equal(await services.done, 23);
  assert.equal(alive(services.children[0].pid), false);
});

test("missing executable fails and cleans up its peer", { timeout: 15000 }, async t => {
  const services = runServices([
    { name: "waiting", command: process.execPath, args: ["-e", "setInterval(()=>{},1000)"] },
    { name: "missing", command: join(tmpdir(), "smartoffice-missing-executable"), args: [] },
  ], { stdio: "ignore" });
  t.after(() => services.stop());
  assert.equal(await services.done, 1);
  assert.equal(alive(services.children[0].pid), false);
});

test("busy port is rejected without stopping its owner", async t => {
  const server = createServer();
  await new Promise(resolve => server.listen(0, "127.0.0.1", resolve));
  t.after(() => new Promise(resolve => server.close(resolve)));
  await assert.rejects(ensurePortFree(server.address().port), /sedang dipakai/);
  assert.equal(server.listening, true);
});
