// Optional Windows compatibility runner when Application Control blocks native SWC.
// NEXT_TEST_WASM_DIR is an upstream internal override, pinned by package-lock.json.
// Standard npm run dev/build remain available on machines that support native SWC.
import { createRequire } from "node:module";
import { dirname } from "node:path";
import { spawn } from "node:child_process";
const require = createRequire(import.meta.url);
const command = process.argv[2];
if (!["dev", "build"].includes(command)) throw new Error("Gunakan dev atau build.");
const child = spawn(process.execPath, [require.resolve("next/dist/bin/next"), command, "--webpack", ...(command === "dev" ? ["--hostname", "127.0.0.1"] : []), ...process.argv.slice(3)], {
  stdio: "inherit",
  env: { ...process.env, NEXT_TEST_WASM_DIR: dirname(require.resolve("@next/swc-wasm-nodejs")) },
});
child.on("exit", code => { process.exitCode = code ?? 1; });
child.on("error", error => { console.error(error.message); process.exitCode = 1; });
