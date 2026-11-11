// End-to-end checks of the demo app in a real browser, desktop and mobile (390 px).
// Run: node tests/e2e/app.e2e.mjs [--shots]   (needs `npm install` and a Chromium for Playwright)
// Fails (exit 1) on: console or page errors, empty screens, horizontal scroll, snake_case outside technical sections,
// tooltips cut off by the viewport, a broken tour, role views that differ from the access policy, alert or lineage
// navigation that does not work, or a value total that differs from the engine.
import { createServer } from "node:http";
import { readFileSync, existsSync, mkdirSync, statSync } from "node:fs";
import { extname, join, resolve } from "node:path";
import { chromium, devices } from "playwright";

const ROOT = resolve(new URL("../..", import.meta.url).pathname);
const APP = join(ROOT, "app");
const SHOTS = join(ROOT, "docs", "capturas");
const takeShots = process.argv.includes("--shots");
const TYPES = { ".html": "text/html", ".js": "text/javascript", ".css": "text/css", ".json": "application/json", ".png": "image/png", ".svg": "image/svg+xml" };
const SCREENS = ["inicio", "alerta/pii-approver_email", "catalogo", "catalogo/silver.service_orders/columnas", "catalogo/gold.customer_value/vista",
  "glosario", "glosario/margen-bruto", "linaje", "calidad", "cuarentena", "contratos", "contratos/gold.service_order_economics/historial",
  "roles", "madurez", "bitacora", "valor", "acerca"];
const SHOT_LIST = { desktop: ["inicio", "alerta/pii-approver_email", "catalogo", "catalogo/silver.service_orders/columnas", "glosario/margen-bruto",
  "linaje", "calidad", "cuarentena", "contratos/gold.service_order_economics/historial", "roles", "madurez", "bitacora", "valor", "acerca"],
  mobile: ["inicio", "linaje", "calidad", "valor"] };
const SNAKE = /\b[a-z0-9]+_[a-z0-9_]+\b/;

const failures = [];
const check = (ok, msg) => { if (!ok) failures.push(msg); };
const json = (name) => JSON.parse(readFileSync(join(APP, "data", `${name}.json`), "utf8"));

const server = createServer((req, res) => {
  const path = decodeURIComponent(new URL(req.url, "http://x").pathname);
  let file = join(APP, path === "/" ? "index.html" : path);
  if (existsSync(file) && statSync(file).isDirectory()) file = join(file, "index.html");
  if (!file.startsWith(APP) || !existsSync(file)) { res.writeHead(404); res.end(); return; }
  res.writeHead(200, { "content-type": TYPES[extname(file)] || "application/octet-stream" });
  res.end(readFileSync(file));
}).listen(0);
const BASE = `http://127.0.0.1:${server.address().port}/`;

async function visibleSnake(page) {
  return page.evaluate((src) => {
    const re = new RegExp(src);
    const walker = document.createTreeWalker(document.querySelector("main"), NodeFilter.SHOW_TEXT);
    const hits = [];
    for (let n = walker.nextNode(); n; n = walker.nextNode()) {
      const el = n.parentElement;
      if (!el || el.closest("[data-tecnico], code, pre, details:not([open]), [hidden]") || !el.offsetParent) continue;
      const m = n.textContent.match(re); if (m) hits.push(m[0]);
    }
    return hits;
  }, SNAKE.source);
}

async function run(kind, contextOptions) {
  const browser = await chromium.launch();
  const ctx = await browser.newContext(contextOptions);
  const page = await ctx.newPage(); page.setDefaultTimeout(6000);
  const errors = [];
  page.on("console", (m) => { if (m.type() === "error") errors.push(m.text()); });
  page.on("pageerror", (e) => errors.push(String(e)));
  const W = contextOptions.viewport.width;

  for (const route of SCREENS) {
    await page.goto(`${BASE}?tour=0#/${route}`);
    await page.waitForSelector("main h1");
    const h1 = (await page.locator("main h1").first().innerText()).trim();
    check(h1.length > 3, `[${kind}] ${route}: empty title`);
    const text = (await page.locator("main").innerText()).trim();
    check(text.length > 200, `[${kind}] ${route}: screen looks empty`);
    const [sw, iw] = await page.evaluate(() => [document.documentElement.scrollWidth, window.innerWidth]);
    check(sw <= iw, `[${kind}] ${route}: horizontal scroll (${sw} > ${iw})`);
    const snake = await visibleSnake(page);
    check(snake.length === 0, `[${kind}] ${route}: snake_case outside technical sections: ${snake.slice(0, 3)}`);
    if (kind === "desktop") {
      const tips = page.locator("main [data-tip]");
      const n = Math.min(await tips.count(), 4);
      for (let i = 0; i < n; i++) {
        const el = tips.nth(i);
        if (!(await el.isVisible())) continue;
        await el.scrollIntoViewIfNeeded(); await el.hover();
        const box = await page.locator("#tip").boundingBox();
        check(box && box.x >= 0 && box.y >= 0 && box.x + box.width <= W && box.y + box.height <= contextOptions.viewport.height,
          `[${kind}] ${route}: tooltip ${i} cut off`);
      }
    }
    if (takeShots && SHOT_LIST[kind].includes(route)) {
      mkdirSync(SHOTS, { recursive: true });
      await page.mouse.move(0, 0);
      await page.screenshot({ path: join(SHOTS, `${kind}-${route.replace(/[/.]/g, "-")}.png`) });
    }
  }

  // Tour: shows on first visit, five steps, then never again.
  await page.goto(`${BASE}?tour=1#/inicio`);
  await page.waitForSelector("#tour-box");
  for (let i = 0; i < 5; i++) await page.click("#tour-next");
  check(await page.locator("#tour-box").isHidden(), `[${kind}] tour did not close`);
  check((await page.evaluate(() => localStorage.getItem("tour_done"))) === "1", `[${kind}] tour not remembered`);
  await page.goto(`${BASE}#/inicio`); await page.waitForSelector("main h1"); await page.waitForTimeout(500);
  check((await page.locator("#tour-box").count()) === 0 || await page.locator("#tour-box").isHidden(), `[${kind}] tour shown again after closing`);

  // Alert click opens its details.
  await page.click("#first-alert");
  await page.waitForFunction(() => location.hash.startsWith("#/alerta/"));
  check((await page.locator("main dl").innerText()).length > 50, `[${kind}] alert details empty`);

  // Lineage node click opens the table.
  await page.goto(`${BASE}#/linaje`); await page.waitForSelector(".lin-node.clickable");
  await page.locator('.lin-node.clickable[data-id="silver.service_orders"]').click();
  await page.waitForFunction(() => location.hash.startsWith("#/catalogo/silver.service_orders"));

  // Role switch hides exactly what the access policy says.
  const access = json("access"); const catalog = json("catalog");
  for (const persona of access.personas) {
    await page.goto(`${BASE}#/inicio`); await page.waitForSelector("main h1");
    await page.selectOption("#persona", persona.role);
    for (const id of ["silver.service_orders", "gold.service_order_economics", "silver.technicians"]) {
      await page.goto(`${BASE}#/catalogo/${id}/vista`); await page.waitForSelector("main h1");
      const view = persona.datasets[id];
      if (!view.level) {
        check(await page.locator("main .notice").isVisible(), `[${kind}] ${persona.role} should have no access to ${id}`);
        continue;
      }
      const ds = catalog.datasets.find((d) => d.id === id);
      const hidden = Object.values(view.columns).filter((v) => v === "hidden").length;
      const locks = await page.locator("main td .cell-hidden").count();
      check(locks === hidden * ds.sample.length, `[${kind}] ${persona.role} on ${id}: ${locks} hidden cells, expected ${hidden * ds.sample.length}`);
    }
    await page.goto(`${BASE}#/cuarentena`); await page.waitForSelector("main h1");
    const disabled = await page.locator("button[data-q]").first().isDisabled();
    check(disabled === !persona.can_act_on_quarantine, `[${kind}] ${persona.role}: quarantine buttons ${disabled ? "disabled" : "enabled"} against the policy`);
  }
  await page.selectOption("#persona", "data_owner");

  // Value: JavaScript formula equals the engine's.
  await page.goto(`${BASE}#/valor`); await page.waitForSelector("#value-total", { state: "attached" });
  const pen = Number(await page.locator("#value-total").getAttribute("data-pen"));
  check(pen === json("value").result.total_pen, `[${kind}] value in browser ${pen} differs from engine ${json("value").result.total_pen}`);

  check(errors.length === 0, `[${kind}] console errors: ${errors.slice(0, 3).join(" | ")}`);
  await browser.close();
}

try {
  await run("desktop", { viewport: { width: 1360, height: 900 } });
  await run("mobile", { ...devices["iPhone 13"], viewport: { width: 390, height: 844 } });
} catch (err) {
  failures.push(`crash: ${err.message}`);
} finally {
  server.close();
}
if (failures.length) { console.error(`FAILED (${failures.length})\n- ${failures.join("\n- ")}`); process.exit(1); }
console.log("All end-to-end checks passed (desktop and mobile).");
