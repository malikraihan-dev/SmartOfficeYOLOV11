import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { createServer } from "node:net";
import { createRequire } from "node:module";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const webRoot = fileURLToPath(new URL("../", import.meta.url));
const projectRoot = resolve(webRoot, "../..");
const require = createRequire(import.meta.url);

export function ensurePortFree(port) {
  return new Promise((resolvePort, reject) => {
    const server = createServer();
    server.once("error", () => reject(new Error(`Port ${port} sedang dipakai. Hentikan server lama terlebih dahulu; launcher tidak menghentikan proses lain.`)));
    server.listen({ host: "127.0.0.1", port, exclusive: true }, () => server.close(resolvePort));
  });
}

// Track only children created here. A failed service shuts down its peer too.
export function runServices(services, { stdio = "inherit" } = {}) {
  const children = [];
  const closed = [];
  let stopping;
  let finish;
  const done = new Promise(resolveDone => { finish = resolveDone; });
  function stop(code = 0) {
    if (stopping) return stopping;
    stopping = (async () => {
      await Promise.all(children.map(child => {
        if (!child.pid || child.exitCode !== null || child.signalCode !== null) return;
        if (process.platform === "win32") {
          return new Promise(resolveKill => {
            const killer = spawn("taskkill", ["/PID", String(child.pid), "/T", "/F"], { windowsHide: true, stdio: "ignore" });
            killer.once("error", () => { child.kill(); resolveKill(); });
            killer.once("close", status => { if (status && child.exitCode === null && child.signalCode === null) child.kill(); resolveKill(); });
          });
        }
        try { process.kill(-child.pid, "SIGKILL"); } catch (error) { if (error.code !== "ESRCH") child.kill("SIGKILL"); }
      }));
      await Promise.all(closed);
      finish(code);
    })();
    return stopping;
  }
  for (const service of services) {
    const child = spawn(service.command, service.args, {
      cwd: service.cwd, env: { ...process.env, ...service.env }, stdio,
      windowsHide: true, detached: process.platform !== "win32",
    });
    children.push(child);
    closed.push(new Promise(resolveClose => child.once("close", resolveClose)));
    child.once("error", error => {
      console.error(`[${service.name}] ${error.message}`);
      void stop(1);
    });
    child.once("exit", code => {
      if (!stopping) {
        console.error(`[${service.name}] berhenti (${code ?? "sinyal"}). Menghentikan layanan lainnya.`);
        void stop(code || 1);
      }
    });
  }
  return { children, done, stop };
}

async function main() {
  const args = process.argv.slice(2).filter(arg => arg !== "--compat");
  const compat = process.platform === "win32" || process.argv.includes("--compat");
  const portFlag = args.findIndex(arg => arg === "--port" || arg === "-p");
  const port = Number(portFlag >= 0 ? args[portFlag + 1] : args.find(arg => arg.startsWith("--port="))?.split("=")[1] ?? process.env.PORT ?? 3000);
  if (!Number.isInteger(port) || port < 1 || port > 65535 || port === 5000) throw new Error("Port frontend harus 1–65535 dan berbeda dari port backend 5000.");
  await Promise.all([ensurePortFree(5000), ensurePortFree(port)]);
  const venv = process.env.VIRTUAL_ENV || join(projectRoot, ".venv");
  const venvPython = join(venv, process.platform === "win32" ? "Scripts/python.exe" : "bin/python");
  const python = process.env.SMARTOFFICE_PYTHON || (existsSync(venvPython) ? venvPython : "python");
  const nextEnv = { SMARTOFFICE_API_URL: "http://127.0.0.1:5000" };
  if (compat) nextEnv.NEXT_TEST_WASM_DIR = dirname(require.resolve("@next/swc-wasm-nodejs"));
  const nextCli = require.resolve("next/dist/bin/next");
  console.log(`Smart Office: web http://127.0.0.1:${port}/login | API http://127.0.0.1:5000`);
  console.log(`Python: ${python}. Ctrl+C menghentikan kedua layanan. Mode ini selalu memakai API lokal.`);
  const services = runServices([
    { name: "Python", command: python, args: ["-u", join(projectRoot, "app.py")], cwd: projectRoot, env: { SMARTOFFICE_WEB_ORIGIN: `http://127.0.0.1:${port},http://localhost:${port}` } },
    { name: "Next.js", command: process.execPath, args: [nextCli, "dev", "--webpack", "--hostname", "127.0.0.1", ...args], cwd: webRoot, env: nextEnv },
  ]);
  const shutdown = () => { console.log("\nMenghentikan Smart Office…"); void services.stop(); };
  process.once("SIGINT", shutdown);
  process.once("SIGTERM", shutdown);
  process.exitCode = await services.done;
  process.removeListener("SIGINT", shutdown);
  process.removeListener("SIGTERM", shutdown);
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main().catch(error => { console.error(error.message); process.exitCode = 1; });
}
