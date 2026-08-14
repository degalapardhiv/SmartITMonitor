const BASE_API = "http://localhost:8000";
const BASE_UI = "http://localhost";

import { readFileSync } from "node:fs";
import { join } from "node:path";

function readLocalEnvPassword() {
  try {
    const body = readFileSync(join(process.cwd(), "..", "backend", ".env"), "utf8");
    const match = body.match(/^ADMIN_PASSWORD\s*=\s*(.+)\s*$/m);
    if (match) return match[1].trim().replace(/^["']|["']$/g, "");
  } catch {}
  return "";
}

const CREDS = {
  username: process.env.SMOKE_USER || "admin",
  password: process.env.SMOKE_PASSWORD || readLocalEnvPassword(),
};

const ROUTES = [
  "/",
  "/devices",
  "/devices/1",
  "/departments",
  "/alerts",
  "/alert-center",
  "/threats",
  "/web-access",
  "/endpoint-activity",
  "/software-deployment",
  "/reports",
  "/settings",
  "/email-history",
  "/notification-history",
  "/network-discovery",
  "/cctv",
  "/os-deployment",
  "/usb-approval",
  "/exam-mode",
  "/lab2",
];

const results = [];

let failures = 0;

function record(name, ok, detail = "") {
  results.push({ name, ok, detail });
  if (!ok) failures += 1;
  const label = ok ? "PASS" : "FAIL";
  console.log(`[${label}] ${name}${detail ? ` - ${detail}` : ""}`);
}

async function run(name, fn) {
  try {
    const outcome = await fn();
    record(name, outcome.ok, outcome.detail);
  } catch (err) {
    record(name, false, err.message);
  }
}

async function login() {
  const body = new URLSearchParams(CREDS);
  const res = await fetch(`${BASE_API}/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: body.toString(),
  });
  const data = await res.json().catch(() => ({}));
  if (res.status !== 200) {
    return { ok: false, detail: `status ${res.status}` };
  }
  if (!data.access_token) {
    return { ok: false, detail: "no access_token in response" };
  }
  return { ok: true };
}

async function authGuard() {
  const res = await fetch(`${BASE_API}/devices`);
  if (res.status !== 401) {
    return { ok: false, detail: `expected 401, got ${res.status}` };
  }
  return { ok: true };
}

async function checkRoutes() {
  for (const route of ROUTES) {
    const res = await fetch(`${BASE_UI}${route}`);
    const body = await res.text();
    const isSpa = res.status === 200 && body.includes('id="root"');
    record(
      `route ${route}`,
      isSpa,
      res.status !== 200 ? `status ${res.status}` : ""
    );
  }
  return { ok: true };
}

async function checkBundle() {
  const index = await (await fetch(`${BASE_UI}/`)).text();
  const match = index.match(/src="(\/assets\/index-[^"]+\.js)"/);
  if (!match) {
    return { ok: false, detail: "could not find bundle src in index.html" };
  }
  const res = await fetch(`${BASE_UI}${match[1]}`);
  if (res.status !== 200) {
    return { ok: false, detail: `${match[1]} status ${res.status}` };
  }
  const type = res.headers.get("content-type") || "";
  if (!type.includes("javascript")) {
    return { ok: false, detail: `${match[1]} content-type ${type}` };
  }
  return { ok: true, detail: match[1] };
}

async function main() {
  console.log("SmartITMonitor frontend smoke test");
  console.log(`targeting UI ${BASE_UI} / API ${BASE_API}`);
  console.log("");

  await run("login (POST /login admin)", login);
  await run("auth guard (/devices without token -> 401)", authGuard);
  await run("SPA routes serve index.html", checkRoutes);
  await run("main bundle serves", checkBundle);

  console.log("");
  const passed = results.filter((r) => r.ok).length;
  console.log(`${passed}/${results.length} checks passed`);
  process.exit(failures === 0 ? 0 : 1);
}

main();
