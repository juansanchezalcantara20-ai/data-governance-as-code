// govkit demo app. Static, no backend: every number comes from data/*.json, produced by `python -m govkit export-app`.
import { compute } from "./value.js";

const FILES = ["meta", "roles", "access", "glossary", "catalog", "contracts", "quality", "quarantine", "lineage",
  "maturity", "alerts", "value", "kpi_catalog", "changes"];
const NAV = [["inicio", "⌂"], ["catalogo", "▤"], ["glosario", "Aa"], ["linaje", "⇶"], ["calidad", "✓"],
  ["cuarentena", "⏸"], ["contratos", "§"], ["roles", "☷"], ["madurez", "◎"], ["bitacora", "≡"], ["valor", "S/"],
  ["acerca", "?"]];
const KPI_SITE = "https://juansanchezalcantara20-ai.github.io/kpi-catalog-storytelling/";

const store = {
  get(k, d) { try { return localStorage.getItem(k) ?? d; } catch { return d; } },
  set(k, v) { try { localStorage.setItem(k, v); } catch { /* storage unavailable: keep in memory */ } },
};
const S = { lang: store.get("lang", "es"), persona: store.get("persona", "data_owner"), D: {}, T: {}, quarantine: {} };

// ------------------------------------------------------------------ helpers
const $ = (sel, root = document) => root.querySelector(sel);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
function t(path, vars = {}) {
  let v = path.split(".").reduce((o, k) => (o == null ? o : o[k]), S.T);
  if (v == null) return path;
  if (typeof v !== "string") return v;
  return v.replace(/\{(\w+)\}/g, (_, k) => (vars[k] ?? `{${k}}`));
}
const nf = () => new Intl.NumberFormat(S.lang === "es" ? "es-PE" : "en-US", { maximumFractionDigits: 2 });
const num = (x) => nf().format(x);
const pen = (x) => `S/ ${new Intl.NumberFormat(S.lang === "es" ? "es-PE" : "en-US", { maximumFractionDigits: 0 }).format(x)}`;
const outOf = (rate) => t("ui.out_of", { n: num(Math.round(rate)) });
const date = (iso) => new Intl.DateTimeFormat(S.lang === "es" ? "es-PE" : "en-GB", { day: "numeric", month: "long", year: "numeric", timeZone: "UTC" }).format(new Date(`${iso}T00:00:00Z`));
const tip = (text) => `data-tip="${esc(text)}" tabindex="0"`;
const slug = (s) => s.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
const base = (id) => id.split(".").slice(1).join(".");
const layerOf = (id) => (id.includes(":") ? id.split(":")[0] : id.split(".")[0]);
function dsName(id) {
  if (id.startsWith("file:")) return `${t("layers.file")}: ${t(`datasets.${id.slice(5).replace(/\.csv$/, "")}`)}`;
  if (id.startsWith("exposure:")) return t(`exposures.${id.slice(9)}`);
  return t(`datasets.${base(id)}`);
}
const colName = (c) => t(`columns.${c}`);
const layerChip = (id) => { const l = layerOf(id); return `<span class="chip layer-${l}" ${tip(t(`layer_hint.${l}`))}>${esc(t(`layers.${l}`))}</span>`; };
const clsChip = (c) => `<span class="chip neutral" ${tip(t(`classification_hint.${c}`))}>${esc(t(`classification_levels.${c}`))}</span>`;
const roleName = (r) => t(`roles.${r}.name`);
const decides = (role, domain) => t("decides_text", { role: roleName(role), domain: t(`domains.${domain}`) });
function jargon(text) {
  return Object.keys(S.T.jargon || {}).reduce((s, k) => s.replace(new RegExp(`(^|[^\\w>])(${k.replace(".", "\\.")})(?=[^\\w]|$)`, "g"),
    (m, pre, w) => `${pre}<abbr ${tip(S.T.jargon[k])}>${w}</abbr>`), esc(text));
}
const tecnico = (html) => `<details class="tech" data-tecnico><summary>${esc(t("ui.technical_detail"))}</summary>${html}</details>`;
function sev(s) { return { high: "bad", medium: "warn", low: "neutral" }[s] || "neutral"; }
function statusChip(st) {
  const cls = { pass: "ok", fail: "bad", warn: "warn" }[st] || "neutral";
  return `<span class="chip ${cls}">${esc(t(`status_text.${st}`))}</span>`;
}
function scoreDot(score) {
  if (score == null) return `<span class="dot neutral" ${tip(t("screens.catalogo.no_contract"))}></span>`;
  const c = score >= 99.9 ? "ok" : score >= 99 ? "warn" : "bad";
  return `<span class="dot ${c}" ${tip(`${t("screens.catalogo.score_label")}: ${num(score)}`)}></span>`;
}
function ruleText(r) {
  const a = r.args || {};
  const vars = { column: r.column ? colName(r.column) : "" };
  if (r.kind === "validValues") vars.values = a.values.map((v) => (typeof v === "string" ? v.toLowerCase() : v)).join(", ");
  if (r.kind === "range") {
    vars.range = "min" in a && "max" in a ? t("range_text.between", { min: num(a.min), max: num(a.max) })
      : "min" in a ? t("range_text.min", { min: num(a.min) }) : t("range_text.max", { max: num(a.max) });
  }
  if (r.kind === "references") vars.target = dsName(a.table);
  if (r.kind === "tolerance") { vars.target = dsName(a.referenceTable); vars.pct = num(a.maxDeviationPct); }
  if (r.kind === "rowCount") vars.min = num(a.min);
  if (r.kind === "freshness") vars.days = num(a.maxAgeDays);
  return t(`rule_text.${r.kind}`, vars);
}
const ruleById = (dataset, rule) => S.D.quality.rules.find((r) => r.dataset === dataset && r.rule === rule);
const termBySlug = (s) => S.D.glossary.terms.find((x) => slug(x.name[S.lang]) === s || slug(x.name.es) === s || x.id === s);
const termByEnName = (n) => S.D.glossary.terms.find((x) => x.name.en === n);
const persona = () => S.D.access.personas.find((p) => p.role === S.persona) || S.D.access.personas[0];
const dataset = (id) => S.D.catalog.datasets.find((d) => d.id === id);
const contract = (id) => S.D.contracts.contracts.find((c) => c.id === id);
const ownerOf = (d) => (d.domain ? decides("data_owner", d.domain) : "—");

function table(headers, rows, opts = {}) {
  const head = headers.map((h) => `<th class="${h.num ? "num" : ""}">${h.label}</th>`).join("");
  const body = rows.map((r) => `<tr ${r.href ? `class="clickable" data-href="${esc(r.href)}"` : ""}>${r.cells.map((c, i) =>
    `<td class="${headers[i].num ? "num" : ""}">${c}</td>`).join("")}</tr>`).join("");
  return `<div class="table-wrap"${opts.id ? ` id="${opts.id}"` : ""}><table><thead><tr>${head}</tr></thead><tbody>${body ||
    `<tr><td colspan="${headers.length}" class="muted">${esc(t("ui.no_results"))}</td></tr>`}</tbody></table></div>`;
}
function toast(msg) {
  const el = $("#toast"); el.textContent = msg; el.hidden = false;
  clearTimeout(toast.h); toast.h = setTimeout(() => { el.hidden = true; }, 3800);
}
function page(title, lead, body) {
  return `<h1>${title}</h1>${lead ? `<p class="lead">${lead}</p>` : ""}<p class="persona-line">${esc(personaSummary())}</p>${body}`;
}
function personaSummary() {
  const p = persona(); let tables = 0, hidden = 0, masked = 0;
  for (const v of Object.values(p.datasets)) {
    if (v.level) tables++;
    for (const c of Object.values(v.columns || {})) { if (c === "hidden" && v.level) hidden++; if (c === "masked") masked++; }
  }
  return `${t(`personas.${p.role}`)} · ${t("persona_summary", { tables, total: Object.keys(p.datasets).length, hidden, masked })}`;
}

// ------------------------------------------------------------------ screens
const screens = {};

screens.inicio = () => {
  const h = S.D.meta.health; const v = S.D.value.result;
  const rate = (100 * h.rules_passing) / h.rules_total;
  const card = (label, stat, detail, href, id) => `<a class="card link" href="${href}"${id ? ` id="${id}"` : ""}><div class="stat-label">${esc(label)}</div>
    <div class="stat">${stat}</div><div class="small muted">${esc(detail)}</div></a>`;
  const alerts = S.D.alerts.alerts.map((a, i) => alertRow(a, i)).join("");
  return page(esc(t("screens.inicio.title", { alerts: S.D.alerts.alerts.length })), esc(t("ui.as_of", { date: date(S.D.meta.as_of) })), `
    <h2>${esc(t("screens.inicio.health"))}</h2>
    <div class="grid g5" id="health">
      ${card(t("screens.inicio.rules"), esc(outOf(rate)), t("screens.inicio.rules_detail", { passing: h.rules_passing, total: h.rules_total }), "#/calidad")}
      ${card(t("screens.inicio.quarantine"), num(h.quarantined_rows), t("screens.inicio.quarantine_detail"), "#/cuarentena")}
      ${card(t("screens.inicio.contracts"), num(h.contracts_active), t("screens.inicio.contracts_detail"), "#/contratos")}
      ${card(t("screens.inicio.terms"), esc(outOf((100 * h.terms_with_owner) / h.terms_total)), t("screens.inicio.terms_detail", { n: h.terms_with_owner, total: h.terms_total }), "#/glosario")}
      ${card(t("screens.inicio.maturity"), num(h.maturity_mean), t("screens.inicio.maturity_detail"), "#/madurez")}
    </div>
    <a class="card link value-card" href="#/valor" id="value-card" style="margin-top:14px">
      <div class="big">${esc(t("value.headline", { hours: num(v.total_hours), pen: pen(v.total_pen) }))}</div>
      <div class="small muted">${esc(t("ui.illustrative"))} · ${esc(t("screens.inicio.value_link"))} →</div></a>
    <h2>${esc(t("screens.inicio.alerts"))} (${S.D.alerts.alerts.length})</h2>
    <p class="small muted">${esc(t("screens.inicio.alerts_hint"))}</p>
    <div class="alerts" id="alerts">${alerts}</div>`);
};

function alertVars(a) {
  const r = a.rule ? ruleById(a.dataset, a.rule) : null;
  return { dataset: dsName(a.dataset), column: a.column ? colName(a.column) : "", rows: num(a.rows),
    evaluated: num(a.evaluated || 0), category: a.category ? t(`personal_data.${a.category}`) : "",
    rule_text: r ? ruleText(r) : "" };
}
function alertRow(a, i) {
  const vars = alertVars(a);
  const title = t(`alerts.${a.kind}.title`, vars);
  return `<a class="alert-row sev-${a.severity}" href="#/alerta/${esc(a.id)}"${i === 0 ? ' id="first-alert"' : ""}>
    <span class="chip ${sev(a.severity)}">${esc(t(`severity.${a.severity}`))}</span>
    <span>${esc(title.charAt(0).toUpperCase() + title.slice(1))}</span>
    <span class="who">${esc(t("ui.who_decides"))}: ${esc(decides(a.decides, a.domain))}</span></a>`;
}

screens.alerta = (id) => {
  const a = S.D.alerts.alerts.find((x) => x.id === id);
  if (!a) return screens.inicio();
  const vars = alertVars(a); const k = `alerts.${a.kind}`;
  const title = t(`${k}.title`, vars);
  return `<p class="breadcrumb"><a href="#/inicio">← ${esc(t("nav.inicio"))}</a></p>
    <h1>${esc(title.charAt(0).toUpperCase() + title.slice(1))}</h1>
    <p><span class="chip ${sev(a.severity)}">${esc(t(`severity.${a.severity}`))}</span></p>
    <div class="card"><dl class="kv">
      <dt>${esc(t("ui.what_happened"))}</dt><dd>${esc(t(`${k}.what`, vars))}</dd>
      <dt>${esc(t("ui.detected_by"))}</dt><dd>${esc(t(`${k}.rule`, vars))}${a.dimension ? ` <span class="chip info" ${tip(t(`dimensions.${a.dimension}.explain`))}>${esc(t(`dimensions.${a.dimension}.name`))}</span>` : ""}</dd>
      <dt>${esc(t("ui.affects"))}</dt><dd><a href="#/catalogo/${esc(a.dataset)}">${esc(dsName(a.dataset))}</a> ${layerChip(a.dataset)}${a.column ? ` · ${esc(colName(a.column))}` : ""} · ${num(a.rows)} ${esc(t("ui.rows"))}
        · <a href="#/linaje/${esc(a.dataset)}">${esc(t("nav.linaje"))}</a></dd>
      <dt>${esc(t("ui.what_to_do"))}</dt><dd>${esc(t(`${k}.todo`))}</dd>
      <dt>${esc(t("ui.who_decides"))}</dt><dd>${esc(decides(a.decides, a.domain))} · <a href="#/roles" ${tip(t(`raci_activities.${a.raci_activity}`))}>${esc(t("raci_activities." + a.raci_activity))}</a></dd>
    </dl>${tecnico(`<pre>${esc(JSON.stringify(a, null, 2))}</pre>`)}</div>`;
};

screens.catalogo = (id, tab) => {
  if (id) return datasetPage(id, tab || "resumen");
  const domains = [...new Set(S.D.catalog.datasets.map((d) => d.domain))];
  const k = S.D.kpi_catalog;
  return page(esc(t("screens.catalogo.title", { n: S.D.catalog.datasets.length })), "", `
    <div class="toolbar"><input type="search" id="q" placeholder="${esc(t("ui.search"))}" aria-label="${esc(t("ui.search"))}">
      <select id="f-domain" aria-label="${esc(t("ui.domain"))}"><option value="">${esc(t("ui.domain"))}: ${esc(t("ui.all"))}</option>
        ${domains.map((d) => `<option value="${d}">${esc(t(`domains.${d}`))}</option>`).join("")}</select>
      <select id="f-layer" aria-label="${esc(t("ui.layer"))}"><option value="">${esc(t("ui.layer"))}: ${esc(t("ui.all"))}</option>
        ${["bronze", "silver", "gold"].map((l) => `<option value="${l}">${esc(t(`layers.${l}`))}</option>`).join("")}</select></div>
    <div id="cat-table"></div>
    <h2>${esc(t("screens.catalogo.kpi_title"))}</h2>
    <div class="card" id="kpi-card"><p>${esc(t("screens.catalogo.kpi_text"))}</p>
      <p><strong>${esc(t("screens.catalogo.kpi_count", { n: k.kpis, rate: num(k.pass_rate) }))}</strong></p>
      ${table([{ label: esc(t("ui.check")) }, { label: esc(t("ui.rule_passes")), num: true }, { label: esc(t("ui.rule_fails")), num: true }],
        k.checks.map((c) => ({ cells: [`<span class="chip neutral">${esc(t(`kpi_families.${c.family}`))}</span> ${esc(t(`kpi_checks.${c.check}`))}`,
          num(c.passed), c.failed ? `<span class="chip bad">${num(c.failed)}</span>` : "0"] })))}
      <p style="margin-top:10px"><a href="${KPI_SITE}" target="_blank" rel="noopener">${esc(t("screens.catalogo.kpi_link"))} ↗</a></p></div>`);
};
function renderCatalogTable() {
  const q = ($("#q")?.value || "").toLowerCase(); const fd = $("#f-domain")?.value; const fl = $("#f-layer")?.value;
  const p = persona();
  const rows = S.D.catalog.datasets.filter((d) => (!fd || d.domain === fd) && (!fl || d.layer === fl) &&
    (!q || `${dsName(d.id)} ${t(`domains.${d.domain}`)} ${d.columns.map((c) => colName(c.name)).join(" ")}`.toLowerCase().includes(q)))
    .map((d) => {
      const access = p.datasets[d.id]?.level;
      return { href: `#/catalogo/${d.id}`, cells: [
        `${access ? "" : `<span ${tip(t("ui.no_access"))}>🔒</span> `}<strong>${esc(dsName(d.id))}</strong>`, layerChip(d.id),
        esc(t(`domains.${d.domain}`)), esc(ownerOf(d)), clsChip(d.classification),
        d.contract_version ? `<span class="chip ok">v${esc(d.contract_version)}</span>` : `<span class="chip neutral" ${tip(t("screens.catalogo.no_contract"))}>—</span>`,
        `${scoreDot(d.quality_score)} ${d.quality_score != null ? num(d.quality_score) : ""}`, num(d.rows)] };
    });
  $("#cat-table").innerHTML = table([{ label: "" }, { label: esc(t("ui.layer")) }, { label: esc(t("ui.domain")) }, { label: esc(t("ui.owner")) },
    { label: esc(t("ui.classification")) }, { label: esc(t("ui.contract")) }, { label: esc(t("ui.quality")) },
    { label: esc(t("screens.catalogo.rows_label")), num: true }], rows);
}

const TABS = ["resumen", "columnas", "calidad", "linaje", "contrato", "uso", "vista"];
const TAB_KEY = { resumen: "summary", columnas: "columns", calidad: "quality", linaje: "lineage", contrato: "contract", uso: "users", vista: "preview" };
function datasetPage(id, tab) {
  const d = dataset(id); if (!d) return screens.catalogo();
  const view = persona().datasets[id] || { level: null, columns: {} };
  const tabs = TABS.map((x) => `<a href="#/catalogo/${id}/${x}" aria-selected="${x === tab}" role="tab">${esc(t(`screens.catalogo.tabs.${TAB_KEY[x]}`))}</a>`).join("");
  let body = "";
  if (tab === "resumen") {
    body = `<div class="card"><dl class="kv">
      <dt>${esc(t("ui.layer"))}</dt><dd>${layerChip(id)}</dd>
      <dt>${esc(t("ui.domain"))}</dt><dd>${esc(t(`domains.${d.domain}`))}</dd>
      <dt>${esc(t("ui.owner"))}</dt><dd>${esc(ownerOf(d))}</dd>
      <dt>${esc(t("ui.steward"))}</dt><dd>${esc(decides("data_steward", d.domain))}</dd>
      <dt>${esc(t("ui.classification"))}</dt><dd>${clsChip(d.classification)}</dd>
      <dt>${esc(t("ui.contract"))}</dt><dd>${d.contract_version ? `<a href="#/contratos/${id}">v${esc(d.contract_version)}</a>` : esc(t("screens.catalogo.no_contract"))}</dd>
      <dt>${esc(t("screens.catalogo.rows_label"))}</dt><dd>${num(d.rows)}</dd>
      <dt>${esc(t("screens.catalogo.quarantined_label"))}</dt><dd>${num(d.quarantined)}</dd>
      <dt>${esc(t("screens.catalogo.score_label"))}</dt><dd>${scoreDot(d.quality_score)} ${d.quality_score != null ? num(d.quality_score) : "—"}</dd>
      ${S.T.contract_text[base(id)] && d.layer !== "bronze" ? `<dt>${esc(t("screens.contratos.promises"))}</dt><dd>${esc(t(`contract_text.${base(id)}`))}</dd>` : ""}
    </dl>${tecnico(`<p class="small">${esc(t("tecnico.table_id"))}: <code>${esc(id)}</code></p>`)}</div>`;
  } else if (tab === "columnas") {
    body = table([{ label: esc(t("ui.column")) }, { label: esc(t("ui.type")) }, { label: esc(t("ui.classification")) }, { label: esc(t("nav.glosario")) }, { label: esc(t("ui.access")) }],
      d.columns.map((c) => {
        const v = view.level ? (view.columns[c.name] || "visible") : "hidden";
        const lock = c.personal_data || c.undeclared_personal_data || ["confidential", "restricted"].includes(c.classification);
        const term = c.business_term ? termByEnName(c.business_term) : null;
        const stateTxt = { visible: "✓", masked: `<span ${tip(t("ui.masked_column"))}>✱ ${esc(t("ui.masked_column"))}</span>`, hidden: `<span class="cell-hidden" ${tip(t("ui.hidden_column"))}>🔒 ${esc(t("ui.hidden_column"))}</span>` }[v];
        return { cells: [`${lock ? `<span ${tip(c.personal_data ? `${t("ui.sensitive")}: ${t(`personal_data.${c.personal_data}`)}` : c.undeclared_personal_data ? `${t("ui.sensitive")}: ${t(`personal_data.${c.undeclared_personal_data}`)}` : t(`classification_hint.${c.classification}`))}>🔒</span> ` : ""}${esc(colName(c.name))}${c.key ? ` <span class="chip info">#</span>` : ""}
`,
          esc(t(`types.${String(c.type).toLowerCase() === "varchar" ? "string" : typeName(c.type)}`)), clsChip(c.classification),
          term ? `<a href="#/glosario/${slug(term.name[S.lang])}">${esc(term.name[S.lang])}</a>` : "—", stateTxt] };
      })) + tecnico(`<p class="small">${esc(t("tecnico.column_id"))}: ${d.columns.map((c) => `<code>${esc(c.name)}</code>`).join(", ")}</p>`);
  } else if (tab === "calidad") {
    const rules = S.D.quality.rules.filter((r) => r.dataset === id);
    body = rules.length ? table([{ label: esc(t("ui.rule")) }, { label: esc(t("screens.calidad.dimension")) }, { label: esc(t("screens.calidad.result")) }, { label: esc(t("screens.calidad.failed_rows")), num: true }],
      rules.map((r) => ({ cells: [esc(ruleText(r)), esc(t(`dimensions.${r.dimension}.name`)), statusChip(r.status), num(r.failed)] })))
      : `<p class="muted">${esc(t("screens.catalogo.no_contract"))}</p>`;
  } else if (tab === "linaje") {
    body = `<div class="grid g2"><div class="card"><h3>${esc(t("screens.catalogo.upstream"))}</h3>${list(d.upstream)}</div>
      <div class="card"><h3>${esc(t("screens.catalogo.downstream"))}</h3>${list(d.downstream)}</div></div>
      <p style="margin-top:12px"><a href="#/linaje/${id}">${esc(t("nav.linaje"))} →</a></p>`;
  } else if (tab === "contrato") {
    body = d.contract_version ? `<p><a href="#/contratos/${id}">${esc(t("ui.contract"))} v${esc(d.contract_version)} →</a></p>` : `<p class="muted">${esc(t("screens.catalogo.no_contract"))}</p>`;
  } else if (tab === "uso") {
    const readers = S.D.access.personas.filter((p) => p.datasets[id]?.level).map((p) => t(`personas.${p.role}`));
    body = `<div class="grid g2"><div class="card"><h3>${esc(t("screens.catalogo.consumers"))}</h3>${d.consumers.length ? `<ul>${d.consumers.map((c) => `<li>${esc(t(`exposures.${c}`))}</li>`).join("")}</ul>` : "<p>—</p>"}</div>
      <div class="card"><h3>${esc(t("ui.view_as"))}</h3><ul>${S.D.access.personas.map((p) => `<li>${esc(t(`personas.${p.role}`))}: ${p.datasets[id]?.level ? "✓" : `🔒 ${esc(t("ui.no_access"))}`}</li>`).join("")}</ul>
      <p class="small muted">${readers.length}/${S.D.access.personas.length}</p></div></div>`;
  } else if (tab === "vista") {
    if (!view.level) body = `<div class="notice">🔒 ${esc(t("ui.no_access"))}</div>`;
    else {
      const cols = d.columns.map((c) => c.name);
      body = `<p class="small muted">${esc(t("screens.catalogo.preview_note"))}</p>` + table(cols.map((c) => ({ label: esc(colName(c)) })),
        d.sample.map((row) => ({ cells: cols.map((c) => {
          const v = view.columns[c] || "visible";
          if (v === "hidden") return `<span class="cell-hidden" ${tip(t("ui.hidden_column"))}>🔒</span>`;
          const val = row[c] === null || row[c] === undefined ? "—" : typeof row[c] === "boolean" ? t(row[c] ? "ui.yes" : "ui.no") : typeof row[c] === "number" ? num(row[c]) : row[c];
          return v === "masked" ? `<span ${tip(t("ui.masked_column"))}>${esc(val)}</span>` : esc(val);
        }) })));
    }
  }
  return `<p class="breadcrumb"><a href="#/catalogo">← ${esc(t("nav.catalogo"))}</a></p>
    <h1>${esc(dsName(id))} ${layerChip(id)}</h1><p class="persona-line">${esc(personaSummary())}</p>
    <nav class="tabs" role="tablist">${tabs}</nav>${body}`;
}
function typeName(dt) {
  const s = String(dt).toUpperCase();
  if (s.includes("INT")) return "integer"; if (s.includes("DOUBLE") || s.includes("DECIMAL")) return "number";
  if (s === "DATE") return "date"; if (s.includes("TIMESTAMP")) return "timestamp"; if (s === "BOOLEAN") return "boolean"; return "string";
}
function list(ids) {
  return ids.length ? `<ul>${ids.map((x) => x.startsWith("file:") || x.startsWith("exposure:") ? `<li>${esc(dsName(x))}</li>`
    : `<li><a href="#/catalogo/${x}">${esc(dsName(x))}</a> ${layerChip(x)}</li>`).join("")}</ul>` : "<p>—</p>";
}

screens.glosario = (s) => {
  if (s) return termPage(s);
  return page(esc(t("screens.glosario.title", { n: S.D.glossary.terms.length })), "", `
    <div class="toolbar"><input type="search" id="q" placeholder="${esc(t("ui.search"))}" aria-label="${esc(t("ui.search"))}">
      <select id="f-kind" aria-label="${esc(t("ui.filter"))}"><option value="">${esc(t("ui.all"))}</option>
        ${["concept", "attribute", "metric"].map((k) => `<option value="${k}">${esc(t(`screens.glosario.kinds.${k}`))}</option>`).join("")}</select>
      <select id="f-status" aria-label="${esc(t("ui.status"))}"><option value="">${esc(t("ui.status"))}: ${esc(t("ui.all"))}</option>
        <option value="approved">${esc(t("status_text.approved"))}</option><option value="draft">${esc(t("status_text.draft"))}</option></select></div>
    <div id="gl-list" class="grid g3"></div>`);
};
function renderGlossary() {
  const q = ($("#q")?.value || "").toLowerCase(); const fk = $("#f-kind")?.value; const fs = $("#f-status")?.value;
  const items = S.D.glossary.terms.filter((x) => (!fk || x.type === fk) && (!fs || x.status === fs) &&
    (!q || `${x.name[S.lang]} ${x.definition[S.lang]} ${x.synonyms.join(" ")}`.toLowerCase().includes(q)));
  $("#gl-list").innerHTML = items.map((x) => `<a class="card link" href="#/glosario/${slug(x.name[S.lang])}">
    <h3>${esc(x.name[S.lang])}</h3><p class="small muted">${esc(t(`screens.glosario.kinds.${x.type}`))} · ${esc(t(`domains.${x.domain}`))}
    · <span class="chip ${x.status === "approved" ? "ok" : "warn"}">${esc(t(`status_text.${x.status}`))}</span></p>
    <p class="small">${esc(x.definition[S.lang])}</p></a>`).join("") || `<p class="muted">${esc(t("ui.no_results"))}</p>`;
}
function termPage(s) {
  const x = termBySlug(s); if (!x) return screens.glosario();
  const L = S.lang; const byId = (id) => S.D.glossary.terms.find((y) => y.id === id);
  const rules = x.source ? x.quality_rules.map((r) => ruleById(x.source.table, r)).filter(Boolean) : [];
  return `<p class="breadcrumb"><a href="#/glosario">← ${esc(t("nav.glosario"))}</a></p>
    <h1>${esc(x.name[L])}</h1><p><span class="chip ${x.status === "approved" ? "ok" : "warn"}">${esc(t(`status_text.${x.status}`))}</span>
    <span class="chip neutral">${esc(t(`screens.glosario.kinds.${x.type}`))}</span></p>
    <div class="card"><dl class="kv">
      <dt>${esc(t("screens.glosario.definition"))}</dt><dd>${esc(x.definition[L])}</dd>
      <dt>${esc(t("screens.glosario.example"))}</dt><dd>${esc(x.example[L])}</dd>
      ${x.formula ? `<dt>${esc(t("screens.glosario.formula"))}</dt><dd>${esc(x.depends_on.length ? x.depends_on.map((d) => byId(d)?.name[L]).join(" · ") : "")}
        ${tecnico(`<code>${esc(x.formula)}</code>`)}</dd>` : ""}
      <dt>${esc(t("ui.owner"))}</dt><dd>${esc(decides("data_owner", x.domain))}</dd>
      <dt>${esc(t("ui.steward"))}</dt><dd>${esc(decides("data_steward", x.domain))}</dd>
      <dt>${esc(t("screens.glosario.lives_in"))}</dt><dd>${x.used_in.length ? x.used_in.map((u) => { const [l, tb, c] = u.split("."); const ds = `${l}.${tb}`;
        return `<a href="#/catalogo/${ds}/columnas">${esc(dsName(ds))}</a> ${layerChip(ds)} · ${esc(colName(c))}`; }).join("<br>") : "—"}</dd>
      <dt>${esc(t("screens.glosario.related"))}</dt><dd>${x.related.map((r) => byId(r)).filter(Boolean).map((r) => `<a href="#/glosario/${slug(r.name[L])}">${esc(r.name[L])}</a>`).join(" · ") || "—"}</dd>
      ${x.synonyms.length ? `<dt>${esc(t("screens.glosario.synonyms"))}</dt><dd>${esc(x.synonyms.join(", "))}</dd>` : ""}
      <dt>${esc(t("screens.glosario.rules"))}</dt><dd>${rules.length ? rules.map((r) => `${esc(ruleText(r))} ${statusChip(r.status)}`).join("<br>") : "—"}</dd>
      <dt>${esc(t("screens.glosario.review"))}</dt><dd>${esc(date(x.next_review))}</dd>
    </dl></div>`;
}

// ------------------------------------------------------------------ lineage
const COLS = ["file", "bronze", "silver", "gold", "exposure"];
screens.linaje = (focus) => {
  const gold = S.D.lineage.column_edges.filter((e) => e[0].startsWith("gold.")).map((e) => `${e[0]}|${e[1]}`);
  const opts = [...new Set(gold)].sort().map((k) => { const [d, c] = k.split("|"); return `<option value="${esc(k)}">${esc(dsName(d))} · ${esc(colName(c))}</option>`; }).join("");
  return page(esc(t("screens.linaje.title")), esc(t("screens.linaje.pick_hint")), `
    <div class="toolbar"><label for="lin-pick" class="small">${esc(t("screens.linaje.pick"))}</label>
      <select id="lin-pick"><option value="">—</option>${opts}</select></div>
    <div class="lineage-wrap" id="lineage">${lineageSvg()}</div>
    <h2>${esc(t("screens.linaje.path"))}</h2><ol class="steps" id="lin-steps"><li class="muted">—</li></ol>`) + `<span hidden id="lin-focus">${esc(focus || "")}</span>`;
};
function layout() {
  const nodes = S.D.lineage.nodes; const pos = {}; const W = 168, H = 34, GX = 44, GY = 14, top = 34;
  COLS.forEach((k, ci) => {
    nodes.filter((n) => n.kind === k).sort((a, b) => (a.domain || "").localeCompare(b.domain || "") || a.id.localeCompare(b.id))
      .forEach((n, ri) => { pos[n.id] = { x: 12 + ci * (W + GX), y: top + ri * (H + GY), w: W, h: H }; });
  });
  const width = 12 + COLS.length * (W + GX) - GX + 12;
  const height = top + Math.max(...Object.values(pos).map((p) => p.y + p.h)) - top + 16;
  return { pos, width, height };
}
function lineageSvg() {
  const { pos, width, height } = layout();
  const edges = S.D.lineage.dataset_edges.map(([s, d]) => {
    const a = pos[s], b = pos[d]; if (!a || !b) return "";
    const x1 = a.x + a.w, y1 = a.y + a.h / 2, x2 = b.x, y2 = b.y + b.h / 2, mx = (x1 + x2) / 2;
    return `<path class="lin-edge" data-s="${esc(s)}" data-d="${esc(d)}" d="M${x1},${y1} C${mx},${y1} ${mx},${y2} ${x2},${y2}"/>`;
  }).join("");
  const heads = COLS.map((k, i) => `<text class="lin-head" x="${12 + i * 212}" y="18">${esc(t(`layers.${k}`))}</text>`).join("");
  const nodes = S.D.lineage.nodes.map((n) => {
    const p = pos[n.id]; const label = dsName(n.id).replace(/^.*?: /, "");
    const click = !n.id.includes(":");
    return `<g class="lin-node k-${n.kind}${click ? " clickable" : ""}" data-id="${esc(n.id)}" transform="translate(${p.x},${p.y})" ${click ? 'tabindex="0" role="link"' : ""}>
      <rect width="${p.w}" height="${p.h}" rx="7"/><text x="10" y="21">${esc(label.length > 23 ? `${label.slice(0, 22)}…` : label)}</text><title>${esc(dsName(n.id))}</title></g>`;
  }).join("");
  return `<svg width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" role="img" aria-label="${esc(t("nav.linaje"))}">${heads}${edges}${nodes}</svg>`;
}
function highlightColumn(key) {
  const svg = $("#lineage svg"); if (!svg) return;
  svg.querySelectorAll(".on,.dim").forEach((e) => e.classList.remove("on", "dim"));
  const steps = $("#lin-steps");
  if (!key) { steps.innerHTML = `<li class="muted">—</li>`; return; }
  const [d0, c0] = key.split("|"); const edges = S.D.lineage.column_edges;
  const seen = new Set([`${d0}.${c0}`]); const datasets = new Set([d0]); const pairs = new Set(); const queue = [[d0, c0]]; const order = [[d0, c0]];
  while (queue.length) {
    const [d, c] = queue.shift();
    for (const e of edges) if (e[0] === d && e[1] === c) {
      const k = `${e[2]}.${e[3]}`; pairs.add(`${e[2]}>${e[0]}`); datasets.add(e[2]);
      if (!seen.has(k)) { seen.add(k); queue.push([e[2], e[3]]); order.push([e[2], e[3]]); }
    }
  }
  S.D.lineage.dataset_edges.forEach(([s, d]) => { if (s === d0 && d.startsWith("exposure:")) { datasets.add(d); pairs.add(`${s}>${d}`); } });
  svg.querySelectorAll(".lin-node").forEach((n) => n.classList.add(datasets.has(n.dataset.id) ? "on" : "dim"));
  svg.querySelectorAll(".lin-edge").forEach((p) => { if (pairs.has(`${p.dataset.s}>${p.dataset.d}`)) p.classList.add("on"); });
  const byDs = {}; order.forEach(([d, c]) => { (byDs[d] ||= []).push(c); });
  const ordered = Object.keys(byDs).sort((a, b) => COLS.indexOf(layerOf(b)) - COLS.indexOf(layerOf(a)));
  steps.innerHTML = ordered.map((d) => {
    const ds = d.includes(":") ? null : dataset(d);
    const rules = ds ? S.D.quality.rules.filter((r) => r.dataset === d).length : 0;
    return `<li>${layerChip(d)} <strong>${ds ? `<a href="#/catalogo/${d}">${esc(dsName(d))}</a>` : esc(dsName(d))}</strong>
      · ${esc([...new Set(byDs[d])].map((c) => colName(c)).join(", "))}
      ${ds ? `<div class="small muted">${esc(t("screens.linaje.step_owner", { owner: ownerOf(ds) }))} · ${esc(t("screens.linaje.step_rules", { n: rules }))}</div>` : ""}</li>`;
  }).join("");
}

// ------------------------------------------------------------------ quality
screens.calidad = () => {
  const Q = S.D.quality; const rules = Q.rules; const passing = rules.filter((r) => r.status === "pass").length;
  const dims = Object.entries(Q.by_dimension).map(([k, v]) => `<div class="card"><h3 ${tip(t(`dimensions.${k}.explain`))}>${esc(t(`dimensions.${k}.name`))}</h3>
    <p class="small muted">${esc(t(`dimensions.${k}.explain`))}</p><div class="stat">${num(v.rules - v.failing_rules)} / ${num(v.rules)}</div>
    <div class="small muted">${esc(t("screens.inicio.rules_detail", { passing: v.rules - v.failing_rules, total: v.rules }))} · ${v.failing_rules ? `<span class="chip bad">${v.failing_rules} ${esc(t("ui.rule_fails"))}</span>` : `<span class="chip ok">${esc(t("ui.rule_passes"))}</span>`}</div></div>`).join("");
  const bars = Object.entries(Q.by_domain).map(([d, v]) => {
    const tot = v.pass + v.fail + v.warn;
    return `<div class="bar-row"><span>${esc(t(`domains.${d}`))}</span><div class="bar" ${tip(`${t("ui.rule_passes")}: ${v.pass} · ${t("ui.rule_warns")}: ${v.warn} · ${t("ui.rule_fails")}: ${v.fail}`)}>
      <span class="p" style="width:${(100 * v.pass) / tot}%"></span><span class="w" style="width:${(100 * v.warn) / tot}%"></span><span class="f" style="width:${(100 * v.fail) / tot}%"></span></div>
      <span class="small">${v.pass} ✓ · ${v.warn} ! · ${v.fail} ✕</span></div>`;
  }).join("");
  return page(esc(t("screens.calidad.title", { passing: num(Math.round((100 * passing) / rules.length)) })), esc(t("ui.as_of", { date: date(Q.as_of) })), `
    <div class="grid g3">${dims}</div>
    <h2>${esc(t("screens.calidad.by_domain"))}</h2><div class="card">${bars}</div>
    <h2>${esc(t("screens.calidad.table", { n: rules.length }))}</h2>
    <div class="toolbar"><input type="search" id="q" placeholder="${esc(t("ui.search"))}" aria-label="${esc(t("ui.search"))}">
      <select id="f-dim" aria-label="${esc(t("screens.calidad.dimension"))}"><option value="">${esc(t("screens.calidad.dimension"))}: ${esc(t("ui.all"))}</option>
        ${Object.keys(Q.by_dimension).map((k) => `<option value="${k}">${esc(t(`dimensions.${k}.name`))}</option>`).join("")}</select>
      <select id="f-status" aria-label="${esc(t("ui.status"))}"><option value="">${esc(t("ui.status"))}: ${esc(t("ui.all"))}</option>
        ${["pass", "warn", "fail"].map((s) => `<option value="${s}">${esc(t(`status_text.${s}`))}</option>`).join("")}</select></div>
    <div id="rules"></div>`);
};
function renderRules() {
  const q = ($("#q")?.value || "").toLowerCase(); const fd = $("#f-dim")?.value; const fs = $("#f-status")?.value;
  const rows = S.D.quality.rules.filter((r) => (!fd || r.dimension === fd) && (!fs || r.status === fs) &&
    (!q || `${dsName(r.dataset)} ${ruleText(r)}`.toLowerCase().includes(q))).map((r) => ({ cells: [
    `<a href="#/catalogo/${r.dataset}/calidad">${esc(dsName(r.dataset))}</a> ${layerChip(r.dataset)}`,
    `${esc(ruleText(r))}${tecnico(`<p class="small">${esc(t("tecnico.rule_id"))}: <code>${esc(r.rule)}</code> · <code>${esc(r.kind)}</code>${r.column ? ` · <code>${esc(r.column)}</code>` : ""}</p><pre>${esc(JSON.stringify(r.args, null, 1))}</pre>`)}`,
    `<span ${tip(t(`dimensions.${r.dimension}.explain`))}>${esc(t(`dimensions.${r.dimension}.name`))}</span>`,
    `<span class="chip ${r.severity === "error" ? "info" : "neutral"}">${esc(t(`severity.${r.severity}`))}</span>`, statusChip(r.status), num(r.failed)] }));
  $("#rules").innerHTML = table([{ label: esc(t("ui.table")) }, { label: esc(t("ui.rule")) }, { label: esc(t("screens.calidad.dimension")) },
    { label: esc(t("ui.severity")) }, { label: esc(t("screens.calidad.result")) }, { label: esc(t("screens.calidad.failed_rows")), num: true }], rows);
}

screens.cuarentena = () => {
  const Q = S.D.quarantine; const p = persona(); const can = p.can_act_on_quarantine;
  const flow = t("quarantine_flow").map((s, i) => `${i ? '<span class="arrow" aria-hidden="true">→</span>' : ""}<span class="step">${esc(s)}</span>`).join("");
  const blocks = Q.tables.map((tb) => `<div class="card" style="margin-bottom:12px"><h3><a href="#/catalogo/${tb.dataset}">${esc(dsName(tb.dataset))}</a> ${layerChip(tb.dataset)} · ${num(tb.rows)} ${esc(t("ui.rows"))}</h3>
    ${table([{ label: esc(t("ui.what_happened")) }, { label: esc(t("ui.rows")), num: true }, { label: esc(t("ui.status")) }, { label: "" }],
      tb.reasons.map((r) => { const rule = ruleById(tb.dataset, r.rule); const key = `${tb.dataset}|${r.rule}`; const st = S.quarantine[key] || "pending";
        return { cells: [esc(rule ? ruleText(rule) : r.rule), num(r.rows), `<span class="chip ${st === "pending" ? "warn" : st === "released" ? "ok" : "neutral"}" data-q-state="${esc(key)}">${esc(t(`quarantine_actions.${st}`))}</span>`,
          `<div class="actions">${["release", "discard"].map((a) => `<button class="btn" data-q="${esc(key)}" data-a="${a}" ${can ? "" : `disabled ${tip(t("ui.read_only_notice"))}`}>${esc(t(`quarantine_actions.${a}`))}</button>`).join("")}</div>`] }; }))}
  </div>`).join("");
  return page(esc(t("screens.cuarentena.title", { n: num(Q.total_rows) })), esc(t("screens.cuarentena.privacy")), `
    <h2>${esc(t("screens.cuarentena.flow"))}</h2><div class="flow">${flow}</div>
    ${can ? "" : `<p class="notice">${esc(t("ui.read_only_notice"))}</p>`}
    <h2>${esc(t("screens.cuarentena.by_reason"))}</h2>${blocks}`);
};

// ------------------------------------------------------------------ contracts
screens.contratos = (id, tab) => {
  if (id) return contractPage(id, tab || "resumen");
  const C = S.D.contracts.contracts;
  return page(esc(t("screens.contratos.title", { n: C.length })), "", `<div class="grid g3">${C.map((c) => `<a class="card link" href="#/contratos/${c.id}">
    <h3>${esc(dsName(c.id))}</h3><p class="small">${layerChip(c.id)} <span class="chip ok">v${esc(c.version)}</span> ${clsChip(c.classification)}</p>
    <p class="small">${esc(t(`contract_text.${base(c.id)}`))}</p></a>`).join("")}</div>`);
};
function contractPage(id, tab) {
  const c = contract(id); if (!c) return screens.contratos();
  const H = S.D.contracts.history;
  const tabs = ["resumen", "tecnico", "historial"].map((x) => `<a href="#/contratos/${id}/${x}" role="tab" aria-selected="${x === tab}">${esc(x === "resumen" ? t("screens.catalogo.tabs.summary") : x === "tecnico" ? t("ui.technical") : t("screens.contratos.history"))}</a>`).join("");
  let body = "";
  if (tab === "resumen") {
    const sla = c.sla ? t(`screens.contratos.freshness_${c.sla.kind === "latency" ? "latency" : "frequency"}`, { value: num(c.sla.value), unit: t(`screens.contratos.units.${c.sla.unit}`) }) : "—";
    body = `<div class="card"><dl class="kv">
      <dt>${esc(t("screens.contratos.promises"))}</dt><dd>${esc(t(`contract_text.${base(id)}`))}</dd>
      <dt>${esc(t("screens.contratos.produces"))}</dt><dd>${esc(decides("data_owner", c.domain))} · ${esc(decides("data_steward", c.domain))}</dd>
      <dt>${esc(t("screens.contratos.consumes"))}</dt><dd>${c.consumers.map((x) => (S.T.exposures[x] ? esc(t(`exposures.${x}`)) : `<a href="#/catalogo/${x}">${esc(dsName(x))}</a>`)).join(" · ") || "—"}</dd>
      <dt>${esc(t("screens.contratos.freshness"))}</dt><dd>${esc(sla)}</dd>
      <dt>${esc(t("ui.classification"))}</dt><dd>${clsChip(c.classification)}</dd>
      <dt>${esc(t("ui.version"))}</dt><dd>v${esc(c.version)} · <span class="chip ok">${esc(t("status_text.active"))}</span></dd>
      <dt>${esc(t("screens.contratos.breaks"))}</dt><dd>${esc(t("screens.contratos.breaks_text"))}</dd>
    </dl></div>
    <h2>${esc(t("screens.catalogo.tabs.columns"))}</h2>
    ${table([{ label: esc(t("ui.column")) }, { label: esc(t("ui.type")) }, { label: esc(t("ui.classification")) }, { label: esc(t("nav.glosario")) }],
      c.columns.map((x) => ({ cells: [`${x.personal_data || ["confidential", "restricted"].includes(x.classification) ? "🔒 " : ""}${esc(colName(x.name))}${x.key ? ' <span class="chip info">#</span>' : ""}${x.required ? ' <span class="chip neutral">*</span>' : ""}`,
        esc(t(`types.${x.logical_type}`)), clsChip(x.classification), x.business_term ? (() => { const tm = termByEnName(x.business_term); return tm ? `<a href="#/glosario/${slug(tm.name[S.lang])}">${esc(tm.name[S.lang])}</a>` : "—"; })() : "—"] })))}`;
  } else if (tab === "tecnico") {
    body = `<div data-tecnico><p class="small muted">${esc(t("tecnico.contract_yaml"))}</p><pre>${esc(c.yaml)}</pre></div>`;
  } else {
    body = `<div class="card"><p>${esc(t("screens.contratos.history_text"))}</p>
      <p><strong>${esc(t("screens.contratos.engine_said"))}</strong> (v${esc(H.from_version)} → v${esc(H.to_version)}):</p>
      <pre data-tecnico>${esc(H.engine_output.join("\n"))}</pre>
      <p><strong>${esc(t("screens.contratos.with_major", { v: H.correct_version }))}</strong>: ${H.correct_output.length ? `<code>${esc(H.correct_output.join(" "))}</code>` : esc(t("screens.contratos.accepted"))}</p>
      <p><a href="#/bitacora">${esc(t("nav.bitacora"))} →</a></p></div>`;
  }
  return `<p class="breadcrumb"><a href="#/contratos">← ${esc(t("nav.contratos"))}</a></p><h1>${esc(dsName(id))} ${layerChip(id)}</h1>
    <nav class="tabs" role="tablist">${tabs}</nav>${body}`;
}

// ------------------------------------------------------------------ roles and access
screens.roles = () => {
  const R = S.D.roles; const A = S.D.access; const roles = R.roles.map((r) => r.id);
  const raci = `<div class="table-wrap raci"><table><thead><tr><th>${esc(t("ui.activity"))}</th>${roles.map((r) => `<th ${tip(t(`roles.${r}.line`))}>${esc(roleName(r))}</th>`).join("")}</tr></thead><tbody>
    ${R.raci.map((a) => `<tr><td>${esc(t(`raci_activities.${a.id}`))}</td>${roles.map((r) => { const l = a.raci[r];
      return `<td class="l ${l || ""}" ${l ? tip(`${roleName(r)}: ${t(`raci_letters.${l}`)}`) : ""}>${l || ""}</td>`; }).join("")}</tr>`).join("")}</tbody></table></div>`;
  const people = `<div class="grid g2">${R.roles.map((r) => `<div class="card"><h3>${esc(roleName(r.id))}</h3><p class="small">${esc(t(`roles.${r.id}.line`))}</p></div>`).join("")}</div>`;
  const doms = R.domains.map((d) => d.id);
  const matrix = table([{ label: esc(t("ui.role")) }, ...doms.map((d) => ({ label: esc(t(`domains.${d}`)) })), { label: esc(t("ui.layer")) }],
    A.matrix.map((m) => ({ cells: [esc(roleName(m.role)) + (m.read_only ? ` <span class="badge ro">${esc(t("read_only_badge"))}</span>` : ""),
      ...doms.map(() => `${clsChip(m.up_to)} <span class="small muted">${esc(m.domains === "all" ? t("screens.roles.all_domains") : t("screens.roles.assigned"))}</span>`),
      m.layers.map((l) => esc(t(`layers.${l}`))).join(", ")] })));
  const checks = A.checks.map((c) => `<li>${c.passed ? "✅" : "❌"} ${esc(t(`screens.roles.checks_list.${c.id}`))}</li>`).join("");
  const ex = A.exceptions.map((e) => `<li>${esc(t("screens.roles.exception_line", { role: roleName(e.role), level: t(`classification_levels.${e.up_to}`),
    domain: t(`domains.${e.domain}`), approver: roleName(e.approved_by_role), expires: date(e.expires_on) }))} ${e.same_person ? '<span class="chip bad">⚠</span>' : '<span class="chip ok">✓</span>'}</li>`).join("");
  return page(esc(t("screens.roles.title")), "", `
    <h2>${jargon("RACI")} · ${esc(t("screens.roles.raci"))}</h2><p class="small muted">${esc(t("screens.roles.raci_hint"))}</p>${raci}
    <h2>${esc(t("screens.roles.people"))}</h2>${people}
    <h2>${esc(t("screens.roles.matrix"))}</h2><p class="small muted">${esc(t("screens.roles.matrix_hint"))}</p>${matrix}
    <div class="grid g2" style="margin-top:14px"><div class="card"><h3>${esc(t("screens.roles.checks"))}</h3><ul>${checks}</ul></div>
      <div class="card"><h3>${esc(t("screens.roles.conflicts"))}</h3><p>${A.sod_conflicts.length ? A.sod_conflicts.map(esc).join("<br>") : esc(t("screens.roles.no_conflicts"))}</p>
      <h3>${esc(t("screens.roles.exceptions"))}</h3><ul>${ex}</ul></div></div>`);
};

screens.madurez = () => {
  const M = S.D.maturity; const mean = M.areas.reduce((s, a) => s + a.score, 0) / M.areas.length;
  const rows = M.areas.map((a) => `<div class="card"><h3>${esc(t(`maturity_areas.${a.id}`))}</h3>
    <p class="small">${esc(t("screens.madurez.current"))}: <strong ${tip(t(`maturity_scale.${a.score}`))}>${a.score}</strong> · ${esc(t("screens.madurez.target"))}: <strong>${a.target}</strong></p>
    <p class="small muted">${esc(t("screens.madurez.next"))}: ${esc(t(`maturity_next.${a.id}`))}</p></div>`).join("");
  const road = [...M.roadmap].sort((a, b) => a.priority - b.priority).map((r) => `<li><span class="chip ${r.priority === 1 ? "bad" : r.priority === 2 ? "warn" : "neutral"}">${esc(t("screens.madurez.priority", { p: r.priority }))}</span>
    ${esc(t(`maturity_areas.${r.area}`))} · <span class="small muted">${esc(t(`screens.madurez.effort.${r.effort}`))}</span>${tecnico(`<p class="small">${esc(r.action)}</p>`)}</li>`).join("");
  return page(esc(t("screens.madurez.title", { mean: num(Math.round(mean * 10) / 10) })), `${jargon("DAMA")} · ${jargon("DMBOK")}`, `
    <div class="grid g2"><div class="card" id="radar">${radar(M.areas)}</div>
      <div class="card"><h3>1–5</h3><ol>${Object.keys(M.scale).map((k) => `<li>${esc(t(`maturity_scale.${k}`))}</li>`).join("")}</ol></div></div>
    <h2>${esc(t("screens.madurez.next"))}</h2><div class="grid g3">${rows}</div>
    <h2>${esc(t("screens.madurez.roadmap"))}</h2><ol class="steps">${road}</ol>`);
};
function radar(areas) {
  const n = areas.length, cx = 210, cy = 200, R = 140;
  const pt = (i, v) => { const ang = -Math.PI / 2 + (2 * Math.PI * i) / n; return [cx + Math.cos(ang) * R * (v / 5), cy + Math.sin(ang) * R * (v / 5)]; };
  const grid = [1, 2, 3, 4, 5].map((lv) => `<polygon class="grid-line" points="${areas.map((_, i) => pt(i, lv).join(",")).join(" ")}"/>`).join("");
  const poly = (key, cls) => `<polygon class="${cls}" points="${areas.map((a, i) => pt(i, a[key]).join(",")).join(" ")}"/>`;
  const labels = areas.map((a, i) => { const [x, y] = pt(i, 6.1); const name = t(`maturity_areas.${a.id}`);
    return `<text x="${x}" y="${y}" text-anchor="${x < cx - 10 ? "end" : x > cx + 10 ? "start" : "middle"}">${esc(name.length > 22 ? `${name.slice(0, 21)}…` : name)}<title>${esc(name)}: ${a.score}</title></text>`; }).join("");
  return `<svg viewBox="-40 0 500 410" width="100%" class="radar" role="img" aria-label="${esc(t("nav.madurez"))}">${grid}${poly("target", "goal")}${poly("score", "now")}${labels}</svg>
    <p class="small"><span style="color:var(--accent)">■</span> ${esc(t("screens.madurez.current"))} · <span style="color:var(--warn)">▢</span> ${esc(t("screens.madurez.target"))}</p>`;
}

screens.bitacora = () => {
  const E = S.D.changes.events;
  return page(esc(t("screens.bitacora.title")), jargon("CI"), `<ul class="timeline">${[...E].reverse().map((e) => `<li class="${e.outcome}">
    <p><span class="chip ${e.outcome === "passed" ? "ok" : "bad"}">${esc(t(`screens.bitacora.outcomes.${e.outcome}`))}</span> <span class="small muted">${esc(date(e.date))}</span></p>
    <p><strong>${esc(S.lang === "es" ? e.title_es : e.title_en)}</strong></p>
    ${e.explanation_es ? `<p class="small">${esc(S.lang === "es" ? e.explanation_es : e.explanation_en)}</p>` : ""}
    ${e.message ? `<p class="small muted">${esc(t("screens.bitacora.message"))}:</p><pre data-tecnico>${esc(e.message)}</pre>` : ""}
    <p class="small"><a href="${esc(e.url)}" target="_blank" rel="noopener">${esc(t("screens.bitacora.see_run"))} ↗</a>
    ${e.pr ? ` · <a href="${esc(S.D.changes.repository)}/pull/${e.pr}" target="_blank" rel="noopener">${esc(t("screens.bitacora.see_pr"))} ↗</a>` : ""}</p></li>`).join("")}</ul>`);
};

// ------------------------------------------------------------------ value
screens.valor = () => {
  const V = S.D.value; const a = S.assumptions || (S.assumptions = Object.fromEntries(Object.entries(V.assumptions).map(([k, x]) => [k, x.value])));
  const sliders = Object.entries(V.assumptions).map(([k, x]) => `<div class="slider"><label for="s-${k}">${esc(x[S.lang])}</label>
    <output id="o-${k}">${num(a[k])}</output><input type="range" id="s-${k}" data-k="${k}" min="${x.min}" max="${x.max}" step="${x.step}" value="${a[k]}"></div>`).join("");
  const rules = V.facts.blocking_rules_fired.map((r) => { const rule = ruleById(r.dataset, r.rule);
    return `<li>${esc(dsName(r.dataset))}: ${esc(rule ? ruleText(rule) : r.rule)} — <strong>${num(r.rows)}</strong> ${esc(t("ui.rows"))}</li>`; }).join("");
  return `<div id="value-root">${valueHeader(compute(V.facts, a))}</div>
    <div class="notice" style="margin:14px 0">${esc(t("ui.illustrative"))}</div>
    <div class="grid g2"><div class="card"><h2 style="margin-top:0">${esc(t("value.assumptions"))}</h2>${sliders}
      <button class="btn" id="reset">${esc(t("value.reset"))}</button></div>
      <div class="card"><h2 style="margin-top:0">${esc(t("value.rules_fired"))}</h2><ul class="small">${rules}</ul>
      <h3>${esc(t("value.how"))}</h3><p class="small muted">${esc(t("value.how_text"))}</p><p class="small">${esc(t("value.legal"))}</p></div></div>`;
};
function valueHeader(r) {
  const F = S.D.value.facts; const part = (k, detail) => `<div class="card"><div class="stat-label">${esc(t(`value.${k}`))}</div>
    <div class="stat">${pen(r.parts[k].pen)}</div><div class="small">${r.parts[k].hours ? `${num(r.parts[k].hours)} ${esc(t("ui.hours"))} · ` : ""}${esc(detail)}</div></div>`;
  return `<h1 id="value-title">${esc(t("screens.valor.title", { hours: num(r.total_hours), pen: pen(r.total_pen) }))}</h1>
    <p class="persona-line">${esc(personaSummary())}</p>
    <div class="grid g2">${part("rework", t("value.rework_detail", { rows: num(r.bad_rows_per_month) }))}
      ${part("wrong_decisions", t("value.wrong_decisions_detail", { count: num(r.parts.wrong_decisions.count) }))}
      ${part("definition_disputes", t("value.definition_disputes_detail", { metrics: F.governed_metrics }))}
      ${part("personal_data_risk", t("value.personal_data_risk_detail", { columns: F.undeclared_pii_columns.length, rows: num(F.undeclared_pii_rows) }))}</div>
    <span hidden id="value-total" data-pen="${r.total_pen}" data-hours="${r.total_hours}"></span>`;
}

screens.acerca = () => {
  const A = "screens.acerca"; const repo = S.D.meta.repository;
  const files = ["01_catalog_and_schemas", "02_tables_from_contracts", "03_classification_tags", "04_grants_from_policy", "05_column_masks"];
  return page(esc(t(`${A}.title`)), "", `
    <div class="grid g2"><div class="card"><h2 style="margin-top:0">✅ ${esc(t(`${A}.real`))}</h2><ul>${t(`${A}.real_items`).map((x) => `<li>${esc(x)}</li>`).join("")}</ul></div>
      <div class="card"><h2 style="margin-top:0">🎭 ${esc(t(`${A}.simulated`))}</h2><ul>${t(`${A}.simulated_items`).map((x) => `<li>${esc(x)}</li>`).join("")}</ul></div></div>
    <h2>${esc(t(`${A}.plan`))}</h2><div class="grid g3">${t(`${A}.plan_items`).map((x) => `<div class="card"><h3>${esc(x.t)}</h3><p class="small">${esc(x.d)}</p></div>`).join("")}</div>
    <h2>${esc(t(`${A}.databricks`))}</h2><div class="card"><p>${esc(t(`${A}.databricks_text`))}</p>
      <ol class="small">${files.map((f) => `<li><a href="${repo}/blob/main/deploy/unity_catalog/${f}.sql" target="_blank" rel="noopener">${esc(f.replace(/^\d+_/, "").replace(/_/g, " "))}</a></li>`).join("")}</ol></div>
    <h2>${esc(t(`${A}.links`))}</h2><ul><li><a href="${repo}" target="_blank" rel="noopener">${esc(t(`${A}.code`))} ↗</a></li>
      <li><a href="docs/" target="_blank" rel="noopener">${esc(t(`${A}.docs`))} ↗</a></li></ul>
    <p class="small muted">${esc(t(`${A}.author`))}</p>`);
};

// ------------------------------------------------------------------ shell
function renderNav(current) {
  $("#nav").innerHTML = NAV.map(([k, ico]) => `<a href="#/${k}" data-nav="${k}" ${k === current ? 'aria-current="page"' : ""}><span class="ico" aria-hidden="true">${ico}</span>${esc(t(`nav.${k}`))}</a>`).join("");
}
function renderShell() {
  document.documentElement.lang = S.lang;
  $("#banner").innerHTML = `${esc(t("ui.banner", { company: S.D.meta.company }))} · <a href="${S.D.meta.repository}" target="_blank" rel="noopener">${esc(t("ui.banner_code"))} ↗</a>`;
  document.querySelectorAll("[data-i18n]").forEach((el) => { el.textContent = t(el.dataset.i18n); });
  document.querySelectorAll("[data-i18n-label]").forEach((el) => { el.setAttribute("aria-label", t(el.dataset.i18nLabel)); el.setAttribute("data-tip", t(el.dataset.i18nLabel)); });
  $("#lang-btn").textContent = t("meta.other");
  $("#persona").innerHTML = S.D.access.personas.map((p) => `<option value="${p.role}" ${p.role === S.persona ? "selected" : ""}>${esc(t(`personas.${p.role}`))}</option>`).join("");
  $("#persona").setAttribute("data-tip", t(`persona_hint.${S.persona}`));
  const ro = $("#ro-badge"); ro.hidden = !persona().read_only; ro.textContent = t("read_only_badge");
}
function route() {
  const parts = (location.hash.replace(/^#\/?/, "") || "inicio").split("/").map(decodeURIComponent);
  const [name, a, b] = parts; const fn = screens[name] || screens.inicio;
  $("#main").innerHTML = fn(a, b);
  renderNav(name === "alerta" ? "inicio" : screens[name] ? name : "inicio");
  $("#nav").classList.remove("open"); $("#menu-btn").setAttribute("aria-expanded", "false");
  wire(name, a);
  if (!route.first) $("#main").focus({ preventScroll: true });
  route.first = false; window.scrollTo(0, 0);
}
route.first = true;
function wire(name, a) {
  document.querySelectorAll("tr[data-href]").forEach((tr) => tr.addEventListener("click", (e) => { if (!e.target.closest("a,button,summary")) location.hash = tr.dataset.href; }));
  if (name === "catalogo" && !a) { ["#q", "#f-domain", "#f-layer"].forEach((s) => $(s).addEventListener("input", renderCatalogTable)); renderCatalogTable(); wire.rows(); }
  if (name === "glosario" && !a) { ["#q", "#f-kind", "#f-status"].forEach((s) => $(s).addEventListener("input", renderGlossary)); renderGlossary(); }
  if (name === "calidad") { ["#q", "#f-dim", "#f-status"].forEach((s) => $(s).addEventListener("input", renderRules)); renderRules(); }
  if (name === "linaje") {
    const sel = $("#lin-pick"); const focus = $("#lin-focus").textContent;
    sel.addEventListener("change", () => highlightColumn(sel.value));
    document.querySelectorAll(".lin-node.clickable").forEach((g) => {
      const go = () => { location.hash = `#/catalogo/${g.dataset.id}`; };
      g.addEventListener("click", go); g.addEventListener("keydown", (e) => { if (e.key === "Enter") go(); });
    });
    const first = focus && S.D.lineage.column_edges.find((e) => e[0] === focus) || S.D.lineage.column_edges.find((e) => e[0] === "gold.site_monthly_kpis" && e[1] === "gross_margin_pct");
    if (first) { sel.value = `${first[0]}|${first[1]}`; highlightColumn(sel.value); }
  }
  if (name === "cuarentena") document.querySelectorAll("button[data-q]").forEach((b) => b.addEventListener("click", () => {
    S.quarantine[b.dataset.q] = b.dataset.a === "release" ? "released" : "discarded";
    const chip = document.querySelector(`[data-q-state="${CSS.escape(b.dataset.q)}"]`);
    chip.textContent = t(`quarantine_actions.${S.quarantine[b.dataset.q]}`); chip.className = `chip ${b.dataset.a === "release" ? "ok" : "neutral"}`;
    toast(t("ui.simulated_action"));
  }));
  if (name === "valor") {
    const V = S.D.value;
    const update = () => { $("#value-root").innerHTML = valueHeader(compute(V.facts, S.assumptions)); };
    document.querySelectorAll("input[type=range]").forEach((r) => r.addEventListener("input", () => {
      S.assumptions[r.dataset.k] = Number(r.value); $(`#o-${r.dataset.k}`).textContent = num(Number(r.value)); update();
    }));
    $("#reset").addEventListener("click", () => { S.assumptions = null; route(); });
  }
}
wire.rows = () => document.querySelectorAll("#cat-table tr[data-href]").forEach((tr) => tr.addEventListener("click", () => { location.hash = tr.dataset.href; }));

// Tooltips: one floating element, clamped to the viewport so it is never cut off.
function setupTips() {
  const el = $("#tip");
  const show = (target) => {
    const text = target.getAttribute("data-tip"); if (!text) return;
    el.textContent = text; el.hidden = false;
    const r = target.getBoundingClientRect(); const w = el.offsetWidth, h = el.offsetHeight;
    let x = Math.min(Math.max(8, r.left + r.width / 2 - w / 2), window.innerWidth - w - 8);
    let y = r.bottom + 8; if (y + h > window.innerHeight - 8) y = Math.max(8, r.top - h - 8);
    el.style.left = `${x}px`; el.style.top = `${y}px`;
  };
  const hide = () => { el.hidden = true; };
  document.addEventListener("mouseover", (e) => { const tg = e.target.closest("[data-tip]"); if (tg) show(tg); else hide(); });
  document.addEventListener("focusin", (e) => { const tg = e.target.closest("[data-tip]"); if (tg) show(tg); });
  document.addEventListener("focusout", hide);
  window.addEventListener("scroll", hide, { passive: true });
}

// Guided tour: five steps on first visit; never shown again once closed.
const TOUR_TARGETS = ["#health", "#first-alert", '[data-nav="linaje"]', "#persona", "#value-card"];
function tour(step = 0) {
  const overlay = $("#tour"); const steps = t("tour.steps");
  let box = $("#tour-box");
  if (!box) { box = document.createElement("div"); box.id = "tour-box"; box.className = "tour-box"; box.setAttribute("role", "dialog");
    box.setAttribute("aria-modal", "true"); box.setAttribute("aria-labelledby", "tour-t"); document.body.appendChild(box); }
  const close = () => { overlay.hidden = true; box.hidden = true; document.querySelectorAll(".tour-hl").forEach((e) => e.classList.remove("tour-hl"));
    $("#nav").classList.remove("open"); store.set("tour_done", "1"); };
  document.querySelectorAll(".tour-hl").forEach((e) => e.classList.remove("tour-hl"));
  if (step >= steps.length) { close(); return; }
  if (!location.hash.startsWith("#/inicio") && location.hash) location.hash = "#/inicio";
  if (step === 2 && window.innerWidth <= 860) $("#nav").classList.add("open"); else $("#nav").classList.remove("open");
  const target = $(TOUR_TARGETS[step]);
  if (target) { target.classList.add("tour-hl"); target.scrollIntoView({ block: "center" }); }
  const s = steps[step];
  overlay.hidden = false; box.hidden = false;
  box.innerHTML = `<p class="small muted">${step + 1} / ${steps.length}</p>
    <h3 id="tour-t">${esc(s.title)}</h3><p>${esc(s.text)}</p><div class="row"><button class="btn" id="tour-skip">${esc(t("tour.skip"))}</button>
    <button class="btn primary" id="tour-next">${esc(step === steps.length - 1 ? t("tour.done") : t("tour.next"))}</button></div>`;
  const r = target ? target.getBoundingClientRect() : null;
  const top = r ? (r.bottom + 12 + box.offsetHeight < window.innerHeight ? r.bottom + 12 : Math.max(12, r.top - box.offsetHeight - 12)) : 80;
  box.style.top = `${top}px`; box.style.left = `${Math.max(16, Math.min((r ? r.left : 16), window.innerWidth - box.offsetWidth - 16))}px`;
  $("#tour-next").onclick = () => tour(step + 1);
  $("#tour-skip").onclick = close;
  $("#tour-next").focus();
}

async function loadLang(lang) { S.T = await (await fetch(`i18n/${lang}.json`)).json(); }
async function main() {
  const theme = store.get("theme", ""); if (theme) document.documentElement.dataset.theme = theme;
  const [_, ...docs] = await Promise.all([loadLang(S.lang), ...FILES.map((f) => fetch(`data/${f}.json`).then((r) => r.json()))]);
  FILES.forEach((f, i) => { S.D[f] = docs[i]; });
  if (!S.D.access.personas.some((p) => p.role === S.persona)) S.persona = "data_owner";
  renderShell(); setupTips(); route();
  window.addEventListener("hashchange", route);
  $("#persona").addEventListener("change", (e) => { S.persona = e.target.value; store.set("persona", S.persona); renderShell(); route(); toast(t(`persona_hint.${S.persona}`)); });
  $("#lang-btn").addEventListener("click", async () => { S.lang = t("meta.other_lang"); store.set("lang", S.lang); await loadLang(S.lang); renderShell(); route(); });
  $("#theme-btn").addEventListener("click", () => {
    const dark = document.documentElement.dataset.theme ? document.documentElement.dataset.theme === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
    document.documentElement.dataset.theme = dark ? "light" : "dark"; store.set("theme", document.documentElement.dataset.theme);
  });
  $("#menu-btn").addEventListener("click", () => { const n = $("#nav"); n.classList.toggle("open"); $("#menu-btn").setAttribute("aria-expanded", String(n.classList.contains("open"))); });
  const params = new URLSearchParams(location.search);
  if (params.get("tour") === "1" || (store.get("tour_done", "") !== "1" && params.get("tour") !== "0" && (!location.hash || location.hash.startsWith("#/inicio")))) setTimeout(() => tour(0), 300);
}
main().catch((err) => { $("#main").innerHTML = `<p class="notice">${esc(String(err))}</p>`; console.error(err); });
