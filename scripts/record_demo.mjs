// Records the README GIF (home → alert → lineage → role switch) and the 1280×640 social preview.
// Run: node scripts/record_demo.mjs   (needs Playwright with Chromium and ffmpeg)
import { createServer } from "node:http";
import { readFileSync, existsSync, mkdirSync, rmSync, statSync, copyFileSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { extname, join, resolve } from "node:path";
import { chromium } from "playwright";

const ROOT = resolve(new URL("..", import.meta.url).pathname);
const APP = join(ROOT, "app");
const OUT = join(ROOT, "docs", "capturas");
const FRAMES = join(ROOT, "data", "gif-frames");
const TYPES = { ".html": "text/html", ".js": "text/javascript", ".css": "text/css", ".json": "application/json", ".png": "image/png" };
const server = createServer((req, res) => {
  const path = decodeURIComponent(new URL(req.url, "http://x").pathname);
  let file = join(APP, path === "/" ? "index.html" : path);
  if (existsSync(file) && statSync(file).isDirectory()) file = join(file, "index.html");
  if (!file.startsWith(APP) || !existsSync(file)) { res.writeHead(404); res.end(); return; }
  res.writeHead(200, { "content-type": TYPES[extname(file)] || "application/octet-stream" }); res.end(readFileSync(file));
}).listen(0);
const BASE = `http://127.0.0.1:${server.address().port}/`;

rmSync(FRAMES, { recursive: true, force: true }); mkdirSync(FRAMES, { recursive: true }); mkdirSync(OUT, { recursive: true });
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1280, height: 760 } });
let n = 0;
const frame = async (count = 1) => { for (let i = 0; i < count; i++) await page.screenshot({ path: join(FRAMES, `f${String(n++).padStart(4, "0")}.png`) }); };
const hold = (seconds) => frame(Math.round(seconds * 2));          // 2 frames per second

await page.goto(`${BASE}?tour=0#/inicio`); await page.waitForSelector("#health"); await page.waitForTimeout(400);
await hold(3);                                                      // home: health and value
await page.hover("#first-alert"); await hold(1);
await page.click("#first-alert"); await page.waitForSelector("main dl"); await page.waitForTimeout(300);
await hold(3.5);                                                    // alert details: what, rule, who decides
await page.goto(`${BASE}?tour=0#/linaje`); await page.waitForSelector(".lin-node"); await page.waitForTimeout(300);
await page.selectOption("#lin-pick", "gold.service_order_economics|gross_margin"); await page.waitForTimeout(300);
await hold(3.5);                                                    // lineage path lit up
await page.goto(`${BASE}?tour=0#/catalogo/silver.service_orders/vista`); await page.waitForSelector("main table"); await page.waitForTimeout(300);
await hold(2);                                                      // owner sees prices
await page.selectOption("#persona", "field_technician"); await page.waitForTimeout(500);
await page.goto(`${BASE}?tour=0#/catalogo/silver.service_orders/vista`); await page.waitForSelector("main table"); await page.waitForTimeout(300);
await hold(3.5);                                                    // technician: money columns locked
await page.selectOption("#persona", "data_owner");

execFileSync("ffmpeg", ["-y", "-loglevel", "error", "-framerate", "2", "-i", join(FRAMES, "f%04d.png"), "-vf",
  "fps=2,scale=960:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=96[p];[b][p]paletteuse=dither=bayer:bayer_scale=4",
  join(OUT, "recorrido.gif")]);

// Social preview 1280×640: a card built from the live app and its real numbers.
const meta = JSON.parse(readFileSync(join(APP, "data", "meta.json"), "utf8"));
const value = JSON.parse(readFileSync(join(APP, "data", "value.json"), "utf8"));
await page.setViewportSize({ width: 1280, height: 760 });
await page.goto(`${BASE}?tour=0#/inicio`); await page.waitForSelector("#health"); await page.waitForTimeout(300);
const shot = (await page.screenshot({ clip: { x: 250, y: 90, width: 1030, height: 560 } })).toString("base64");
const h = meta.health;
const card = await browser.newPage({ viewport: { width: 1280, height: 640 } });
await card.setContent(`<!doctype html><html><body style="margin:0;font-family:system-ui,sans-serif;background:#0f2a33;color:#fff;width:1280px;height:640px;overflow:hidden">
  <div style="padding:96px 0 0 64px;width:560px;position:absolute">
    <div style="font-size:20px;opacity:.75;letter-spacing:.02em">govkit · data-governance-as-code</div>
    <div style="font-size:50px;font-weight:800;line-height:1.08;margin:18px 0">Gobierno de datos<br>como código,<br>navegable</div>
    <div style="font-size:22px;line-height:1.45;opacity:.9">Glosario, contratos, calidad, linaje y accesos verificados en cada cambio.</div>
    <div style="display:flex;gap:26px;margin-top:34px;font-size:18px;opacity:.95">
      <div><b style="font-size:34px">${h.rules_total}</b><br>reglas</div><div><b style="font-size:34px">${h.contracts_active}</b><br>contratos</div>
      <div><b style="font-size:34px">${h.terms_total}</b><br>términos</div><div><b style="font-size:34px">${h.quarantined_rows}</b><br>filas detenidas</div></div>
    <div style="margin-top:30px;font-size:16px;opacity:.7">Datos sintéticos · ${value.result.total_hours} h/mes evitadas (supuestos ilustrativos)</div>
  </div>
  <img src="data:image/png;base64,${shot}" style="position:absolute;left:660px;top:118px;width:760px;border-radius:14px;box-shadow:0 20px 50px rgba(0,0,0,.45)">
</body></html>`);
await card.screenshot({ path: join(OUT, "social.png") });
copyFileSync(join(OUT, "social.png"), join(APP, "social.png"));
await browser.close(); server.close();
rmSync(FRAMES, { recursive: true, force: true });
console.log(`frames: ${n} (${n / 2} s) -> docs/capturas/recorrido.gif, docs/capturas/social.png`);
