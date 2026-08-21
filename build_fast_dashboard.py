from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
HTML_PATH = ROOT / "index.html"
DATA_JSON_PATH = ROOT / "dashboard-data.json"
SUMMARY_JSON_PATH = ROOT / "dashboard-summary.json"


def safe_json_for_script(payload: str) -> str:
    return (
        payload.replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


HTML_TEMPLATE = """<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Отчет по сделкам 2026</title>
  <style>
    :root {
      --bg: #f5f7fa;
      --surface: #ffffff;
      --line: #d9dee7;
      --line-strong: #b8c1cf;
      --text: #18212f;
      --muted: #5d6a7c;
      --soft: #eef2f7;
      --teal: #0f766e;
      --teal-soft: #d9f2ee;
      --blue: #2756a6;
      --blue-soft: #dce8ff;
      --amber: #b7791f;
      --danger: #b42318;
      --shadow: 0 10px 28px rgba(17, 24, 39, 0.08);
    }
    * { box-sizing: border-box; }
    html { min-height: 100%; }
    body {
      margin: 0;
      min-height: 100%;
      background: var(--bg);
      color: var(--text);
      font-family: "Segoe UI", Arial, sans-serif;
      font-size: 14px;
      letter-spacing: 0;
    }
    button, input, select {
      font: inherit;
    }
    button {
      border: 1px solid var(--line);
      background: var(--surface);
      color: var(--text);
      border-radius: 8px;
      min-height: 38px;
      padding: 8px 10px;
      cursor: pointer;
      transition: transform 120ms ease, box-shadow 150ms ease, background-color 150ms ease, border-color 150ms ease;
    }
    button:hover:not(:disabled) {
      transform: translateY(-1px);
      box-shadow: 0 8px 18px rgba(17, 24, 39, 0.12);
    }
    button:active:not(:disabled) {
      transform: translateY(0);
      box-shadow: none;
    }
    button:disabled {
      opacity: 0.55;
      cursor: not-allowed;
    }
    .button-primary {
      background: var(--teal);
      border-color: var(--teal);
      color: #fff;
      font-weight: 700;
    }
    .button-secondary {
      background: var(--soft);
      font-weight: 650;
    }
    .app {
      display: grid;
      grid-template-columns: 330px minmax(0, 1fr);
      min-height: 100vh;
    }
    .sidebar {
      position: sticky;
      top: 0;
      height: 100vh;
      overflow: auto;
      padding: 16px;
      border-right: 1px solid var(--line);
      background: #fbfcfe;
    }
    .main {
      min-width: 0;
      padding: 18px;
    }
    .header {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 16px;
      margin-bottom: 14px;
    }
    h1 {
      margin: 0;
      font-size: 22px;
      line-height: 1.2;
      letter-spacing: 0;
    }
    .subtitle {
      margin-top: 4px;
      color: var(--muted);
      font-size: 13px;
    }
    .status {
      min-width: 190px;
      text-align: right;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.4;
    }
    .status strong {
      color: var(--text);
      font-size: 13px;
    }
    .filter-title {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 8px;
      margin-bottom: 12px;
    }
    .filter-title h2 {
      margin: 0;
      font-size: 17px;
      letter-spacing: 0;
    }
    .dirty-dot {
      display: none;
      padding: 4px 7px;
      border-radius: 999px;
      background: #fff4db;
      color: #7a4b00;
      border: 1px solid #f1d394;
      font-size: 11px;
      font-weight: 700;
    }
    .dirty .dirty-dot { display: inline-flex; }
    .filter-actions {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
      margin-bottom: 12px;
    }
    .filter-group {
      border: 1px solid var(--line);
      background: var(--surface);
      border-radius: 8px;
      margin-bottom: 10px;
      overflow: hidden;
    }
    .filter-group summary {
      list-style: none;
      cursor: pointer;
      padding: 10px 12px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      font-weight: 700;
    }
    .filter-group summary::-webkit-details-marker { display: none; }
    .filter-count {
      color: var(--muted);
      font-size: 12px;
      font-weight: 600;
    }
    .filter-body {
      border-top: 1px solid var(--line);
      padding: 10px;
    }
    .date-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
    }
    label.small {
      display: block;
      color: var(--muted);
      font-size: 12px;
      font-weight: 650;
      margin-bottom: 5px;
    }
    input[type="date"], input[type="search"], input[type="number"], select {
      width: 100%;
      border: 1px solid var(--line);
      background: #fff;
      color: var(--text);
      border-radius: 8px;
      min-height: 36px;
      padding: 7px 9px;
      outline: none;
    }
    input:focus, select:focus {
      border-color: var(--teal);
      box-shadow: 0 0 0 3px rgba(15, 118, 110, 0.12);
    }
    .quick-buttons {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 6px;
      margin-top: 8px;
    }
    .quick-buttons button {
      min-height: 32px;
      padding: 6px 8px;
      font-size: 12px;
      font-weight: 650;
    }
    .filter-tools {
      display: grid;
      grid-template-columns: 1fr auto auto;
      gap: 6px;
      margin-bottom: 8px;
    }
    .filter-tools button {
      min-height: 34px;
      padding: 6px 8px;
      font-size: 12px;
      font-weight: 650;
    }
    .options {
      max-height: 230px;
      overflow: auto;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
      padding: 4px;
    }
    .option {
      display: grid;
      grid-template-columns: 18px minmax(0, 1fr);
      gap: 8px;
      align-items: start;
      min-height: 30px;
      padding: 6px;
      border-radius: 6px;
      cursor: pointer;
      line-height: 1.25;
    }
    .option:hover { background: #f0f6f5; }
    .option input {
      width: 16px;
      height: 16px;
      margin: 0;
      accent-color: var(--teal);
    }
    .option-text {
      min-width: 0;
      overflow-wrap: anywhere;
    }
    .option-count {
      color: var(--muted);
      font-size: 11px;
      margin-left: 4px;
      white-space: nowrap;
    }
    .kpi-row {
      display: grid;
      grid-template-columns: minmax(220px, 360px) minmax(0, 1fr);
      gap: 12px;
      margin-bottom: 12px;
    }
    .kpi-card, .panel {
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: var(--shadow);
    }
    .kpi-card {
      padding: 16px;
    }
    .kpi-label {
      color: var(--muted);
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
    }
    .kpi-value {
      margin-top: 6px;
      font-size: 38px;
      line-height: 1;
      font-weight: 800;
      color: var(--teal);
      font-variant-numeric: tabular-nums;
    }
    .kpi-note {
      margin-top: 8px;
      color: var(--muted);
      font-size: 12px;
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
      align-items: start;
    }
    .panel {
      min-width: 0;
      overflow: hidden;
    }
    .panel-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      padding: 12px 14px;
      border-bottom: 1px solid var(--line);
      background: #fbfcfe;
    }
    .panel-header h3 {
      margin: 0;
      font-size: 15px;
      letter-spacing: 0;
    }
    .panel-header span {
      color: var(--muted);
      font-size: 12px;
      white-space: nowrap;
    }
    .panel-body {
      padding: 12px 14px 14px;
    }
    .wide { grid-column: 1 / -1; }
    .bar-list {
      display: grid;
      gap: 7px;
    }
    .bar-row {
      display: grid;
      grid-template-columns: minmax(110px, 1fr) minmax(120px, 45%) 56px;
      gap: 8px;
      align-items: center;
      min-height: 24px;
    }
    .bar-label {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      color: var(--text);
      font-size: 13px;
    }
    .bar-track {
      height: 10px;
      background: var(--soft);
      border-radius: 999px;
      overflow: hidden;
    }
    .bar-fill {
      height: 100%;
      background: linear-gradient(90deg, var(--teal), var(--blue));
      border-radius: 999px;
      transform-origin: left center;
    }
    .bar-value {
      text-align: right;
      font-variant-numeric: tabular-nums;
      font-weight: 700;
      color: var(--muted);
      font-size: 12px;
    }
    .month-grid {
      display: grid;
      grid-template-columns: repeat(12, minmax(0, 1fr));
      gap: 8px;
      align-items: end;
      height: 180px;
      padding-top: 4px;
    }
    .month-col {
      display: grid;
      grid-template-rows: 1fr auto auto;
      gap: 5px;
      min-width: 0;
      height: 100%;
      text-align: center;
    }
    .month-bar-wrap {
      display: flex;
      align-items: end;
      justify-content: center;
      min-height: 0;
    }
    .month-bar {
      width: min(28px, 78%);
      min-height: 2px;
      border-radius: 6px 6px 0 0;
      background: var(--blue);
    }
    .month-value {
      font-size: 11px;
      color: var(--muted);
      font-weight: 700;
      font-variant-numeric: tabular-nums;
    }
    .month-label {
      font-size: 11px;
      color: var(--muted);
    }
    .table-tools {
      display: grid;
      grid-template-columns: minmax(160px, 1fr) auto auto auto;
      gap: 8px;
      align-items: center;
    }
    .table-wrap {
      overflow: auto;
      max-height: 560px;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      min-width: 900px;
    }
    th, td {
      padding: 8px 10px;
      border-bottom: 1px solid var(--line);
      text-align: left;
      vertical-align: top;
      font-size: 12px;
    }
    th {
      position: sticky;
      top: 0;
      background: #f8fafc;
      color: var(--muted);
      font-weight: 800;
      z-index: 1;
    }
    td.num, th.num {
      text-align: right;
      font-variant-numeric: tabular-nums;
    }
    .empty {
      padding: 24px;
      text-align: center;
      color: var(--muted);
      background: #fbfcfe;
      border: 1px dashed var(--line);
      border-radius: 8px;
    }
    .busy .main {
      cursor: progress;
    }
    .busy .button-primary {
      opacity: 0.82;
    }
    @media (max-width: 1100px) {
      .app { grid-template-columns: 1fr; }
      .sidebar {
        position: static;
        height: auto;
        border-right: 0;
        border-bottom: 1px solid var(--line);
      }
      .grid, .kpi-row { grid-template-columns: 1fr; }
    }
    @media (max-width: 640px) {
      .main, .sidebar { padding: 12px; }
      .header, .table-tools { grid-template-columns: 1fr; display: grid; }
      .status { text-align: left; }
      .date-grid { grid-template-columns: 1fr; }
      .bar-row { grid-template-columns: 1fr 92px 48px; }
      .month-grid { grid-template-columns: repeat(6, minmax(0, 1fr)); height: auto; }
      .month-col { height: 120px; }
    }
  </style>
</head>
<body>
  <div class="app" id="app">
    <aside class="sidebar" id="filters">
      <div class="filter-title">
        <h2>Фильтры</h2>
        <span class="dirty-dot">не применено</span>
      </div>
      <div class="filter-actions">
        <button class="button-primary" id="apply-btn" type="button">Применить</button>
        <button class="button-secondary" id="reset-btn" type="button">Сбросить</button>
      </div>

      <details class="filter-group" open>
        <summary><span>Дата сделки</span><span class="filter-count" id="date-caption">2026</span></summary>
        <div class="filter-body">
          <div class="date-grid">
            <div>
              <label class="small" for="date-from">Дата от</label>
              <input id="date-from" type="date" min="2026-01-01" max="2026-12-31" />
            </div>
            <div>
              <label class="small" for="date-to">Дата до</label>
              <input id="date-to" type="date" min="2026-01-01" max="2026-12-31" />
            </div>
          </div>
          <div class="quick-buttons">
            <button type="button" data-range="all">2026</button>
            <button type="button" data-range="q1">1 кв.</button>
            <button type="button" data-range="q2">2 кв.</button>
            <button type="button" data-range="jan">Янв.</button>
            <button type="button" data-range="feb">Фев.</button>
            <button type="button" data-range="mar">Мар.</button>
          </div>
        </div>
      </details>

      <div id="filter-host"></div>
    </aside>

    <main class="main">
      <header class="header">
        <div>
          <h1>Отчет по сделкам 2026</h1>
          <div class="subtitle">Тюмень, данные из OLD_DATA. Все графики считают только количество сделок.</div>
        </div>
        <div class="status" id="status">Подготовка данных</div>
      </header>

      <section class="kpi-row">
        <div class="kpi-card">
          <div class="kpi-label">Количество сделок</div>
          <div class="kpi-value" id="kpi-count">0</div>
          <div class="kpi-note" id="kpi-note">из 0 сделок в базе</div>
        </div>
      </section>

      <section class="grid">
        <article class="panel">
          <div class="panel-header"><h3>Застройщики</h3><span id="developers-subtitle"></span></div>
          <div class="panel-body" id="chart-developers"></div>
        </article>
        <article class="panel">
          <div class="panel-header"><h3>Объекты</h3><span id="objects-subtitle"></span></div>
          <div class="panel-body" id="chart-objects"></div>
        </article>
        <article class="panel">
          <div class="panel-header"><h3>Районы</h3><span id="districts-subtitle"></span></div>
          <div class="panel-body" id="chart-districts"></div>
        </article>
        <article class="panel">
          <div class="panel-header"><h3>Способ покупки</h3><span id="purchase-subtitle"></span></div>
          <div class="panel-body" id="chart-purchase"></div>
        </article>
        <article class="panel wide">
          <div class="panel-header"><h3>Динамика по месяцам</h3><span id="months-subtitle"></span></div>
          <div class="panel-body" id="chart-months"></div>
        </article>
        <article class="panel wide">
          <div class="panel-header"><h3>Залогодержатели / банки</h3><span id="lenders-subtitle"></span></div>
          <div class="panel-body" id="chart-lenders"></div>
        </article>
        <article class="panel wide">
          <div class="panel-header">
            <h3>Сделки</h3>
            <div class="table-tools">
              <input id="table-search" type="search" placeholder="Поиск по таблице" />
              <button id="export-btn" type="button">CSV</button>
              <button id="prev-page" type="button">Назад</button>
              <button id="next-page" type="button">Вперед</button>
            </div>
          </div>
          <div class="panel-body">
            <div class="status" id="table-status" style="text-align:left; margin-bottom:8px;"></div>
            <div class="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Дата</th>
                    <th>Застройщик</th>
                    <th>Объект</th>
                    <th>Район</th>
                    <th>Способ покупки</th>
                    <th>Банк</th>
                    <th class="num">Площадь</th>
                    <th class="num">Цена сделки</th>
                  </tr>
                </thead>
                <tbody id="deal-rows"></tbody>
              </table>
            </div>
          </div>
        </article>
      </section>
    </main>
  </div>

  <script id="dashboard-summary-data" type="application/json">__SUMMARY_JSON__</script>
  <script id="dashboard-data" type="application/json">__DASHBOARD_DATA_JSON__</script>
  <script type="module">
    const tBoot = performance.now();
    const raw = JSON.parse(document.getElementById("dashboard-data").textContent);
    const fields = raw.dealFields || [];
    const fieldIndex = Object.fromEntries(fields.map((field, index) => [field, index]));
    const stringTable = raw.stringTable || [];
    const stringIndexes = new Set(raw.stringFieldIndexes || []);
    const boolIndexes = new Set(raw.booleanFieldIndexes || []);
    const MONTHS = ["Янв", "Фев", "Мар", "Апр", "Май", "Июн", "Июл", "Авг", "Сен", "Окт", "Ноя", "Дек"];
    const PAGE_SIZE = 100;
    const EMPTY_KEY = "__empty__";

    const $ = (selector) => document.querySelector(selector);
    const formatInt = new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 0 });
    const formatMoney = new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 0 });
    const formatArea = new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 1 });

    function valueAt(row, field) {
      const index = fieldIndex[field];
      if (index === undefined) return "";
      const value = row[index];
      if (stringIndexes.has(index)) {
        return Number.isInteger(value) ? stringTable[value] || "" : String(value || "");
      }
      if (boolIndexes.has(index)) return Boolean(value);
      return value ?? "";
    }

    function normalize(value) {
      return String(value || "")
        .replace(/\\u00a0/g, " ")
        .replace(/\\s+/g, " ")
        .trim()
        .toLowerCase();
    }

    function isMortgage(value) {
      const normalized = normalize(value);
      if (!normalized) return false;
      if (/(^|\\s)(не|без)\\s*ипот/.test(normalized)) return false;
      return normalized.includes("ипот");
    }

    function clampDate(value) {
      const text = String(value || "");
      if (!/^2026-\\d{2}-\\d{2}$/.test(text)) return "";
      if (text < "2026-01-01") return "2026-01-01";
      if (text > "2026-12-31") return "2026-12-31";
      return text;
    }

    function toRecord(row, index) {
      const date = String(valueAt(row, "contract_date") || "");
      const developer = String(valueAt(row, "developer_group_name") || valueAt(row, "developer_name") || "(не указан)");
      const developerId = String(valueAt(row, "developer_group_id") || valueAt(row, "developer_id") || developer);
      const object = String(valueAt(row, "object_group_name") || valueAt(row, "object_name") || "(не указан)");
      const objectId = String(valueAt(row, "object_group_id") || valueAt(row, "object_id") || object);
      const district = String(valueAt(row, "district_name") || "(не указан)");
      const purchase = String(valueAt(row, "purchase_type_raw") || "(не указан)");
      const purchaseKey = isMortgage(purchase) ? "mortgage" : "non_mortgage";
      const lenderRaw = String(valueAt(row, "mortgage_lender_raw") || "");
      const lender = lenderRaw.trim() || "(не указан)";
      const lenderKey = normalize(lenderRaw) || EMPTY_KEY;
      const area = Number(valueAt(row, "deal_area_sqm")) || 0;
      const amount = Number(valueAt(row, "deal_amount")) || 0;
      const search = normalize([date, developer, object, district, purchase, lender, valueAt(row, "contract_number")].join(" "));
      const dateNum = Number(date.replace(/-/g, "")) || 0;
      return { index, date, dateNum, developer, developerId, object, objectId, district, districtKey: normalize(district) || EMPTY_KEY, purchase, purchaseKey, lender, lenderKey, area, amount, search };
    }

    const records = (raw.dealRows || [])
      .map(toRecord)
      .filter((row) => row.date >= "2026-01-01" && row.date <= "2026-12-31");

    const optionDefs = {
      developers: { title: "Застройщики", field: "developerId", label: "developer", search: "" },
      objects: { title: "Объекты", field: "objectId", label: "object", search: "" },
      districts: { title: "Районы", field: "districtKey", label: "district", search: "" },
      purchases: { title: "Способ покупки", field: "purchaseKey", label: "purchase", search: "" },
      lenders: { title: "Залогодержатели / банки", field: "lenderKey", label: "lender", search: "" }
    };

    const options = buildAllOptions(records);
    const state = {
      draft: blankFilters(),
      applied: blankFilters(),
      filtered: records,
      sorted: [],
      tableQuery: "",
      tablePage: 1,
      renderToken: 0
    };

    function blankFilters() {
      return {
        from: "",
        to: "",
        developers: new Set(),
        objects: new Set(),
        districts: new Set(),
        purchases: new Set(),
        lenders: new Set()
      };
    }

    function cloneFilters(filters) {
      return {
        from: filters.from,
        to: filters.to,
        developers: new Set(filters.developers),
        objects: new Set(filters.objects),
        districts: new Set(filters.districts),
        purchases: new Set(filters.purchases),
        lenders: new Set(filters.lenders)
      };
    }

    function buildAllOptions(rows) {
      const result = {};
      for (const key of Object.keys(optionDefs)) {
        const def = optionDefs[key];
        const map = new Map();
        for (const row of rows) {
          const id = String(row[def.field] || EMPTY_KEY);
          if (!map.has(id)) map.set(id, { id, label: String(row[def.label] || "(не указан)"), count: 0 });
          map.get(id).count += 1;
        }
        if (key === "purchases") {
          const mortgage = map.get("mortgage") || { id: "mortgage", label: "Ипотека", count: 0 };
          const nonMortgage = map.get("non_mortgage") || { id: "non_mortgage", label: "Не ипотека", count: 0 };
          mortgage.label = "Ипотека";
          nonMortgage.label = "Не ипотека";
          result[key] = [mortgage, nonMortgage];
        } else {
          result[key] = Array.from(map.values()).sort((a, b) => b.count - a.count || a.label.localeCompare(b.label, "ru"));
        }
      }
      return result;
    }

    function selectedCaption(set, total) {
      return set.size ? `${formatInt.format(set.size)} из ${formatInt.format(total)}` : "все";
    }

    function renderFilterHost() {
      const host = $("#filter-host");
      host.innerHTML = Object.entries(optionDefs).map(([key, def]) => `
        <details class="filter-group" ${key === "developers" || key === "purchases" ? "open" : ""}>
          <summary><span>${def.title}</span><span class="filter-count" id="${key}-caption"></span></summary>
          <div class="filter-body">
            <div class="filter-tools">
              <input type="search" data-option-search="${key}" placeholder="Найти" />
              <button type="button" data-select-visible="${key}">Все</button>
              <button type="button" data-clear-filter="${key}">Снять</button>
            </div>
            <div class="options" id="${key}-options"></div>
          </div>
        </details>
      `).join("");
      host.addEventListener("input", (event) => {
        const key = event.target.dataset.optionSearch;
        if (!key) return;
        optionDefs[key].search = event.target.value;
        renderOptions(key);
      });
      host.addEventListener("click", (event) => {
        const selectKey = event.target.dataset.selectVisible;
        const clearKey = event.target.dataset.clearFilter;
        if (selectKey) {
          visibleOptions(selectKey).forEach((option) => state.draft[selectKey].add(option.id));
          markDirty();
          renderOptions(selectKey);
        }
        if (clearKey) {
          state.draft[clearKey].clear();
          markDirty();
          renderOptions(clearKey);
        }
      });
      host.addEventListener("change", (event) => {
        const key = event.target.dataset.optionKey;
        if (!key) return;
        const id = event.target.value;
        if (event.target.checked) state.draft[key].add(id);
        else state.draft[key].delete(id);
        markDirty();
        updateCaptions();
      });
      Object.keys(optionDefs).forEach(renderOptions);
      updateCaptions();
    }

    function visibleOptions(key) {
      const query = normalize(optionDefs[key].search);
      return options[key].filter((option) => !query || normalize(option.label).includes(query));
    }

    function renderOptions(key) {
      const node = $(`#${key}-options`);
      const selected = state.draft[key];
      const visible = visibleOptions(key);
      if (!visible.length) {
        node.innerHTML = `<div class="empty">Нет вариантов</div>`;
        updateCaptions();
        return;
      }
      const html = visible.map((option) => `
        <label class="option" title="${escapeHtml(option.label)}">
          <input type="checkbox" data-option-key="${key}" value="${escapeHtml(option.id)}" ${selected.has(option.id) ? "checked" : ""} />
          <span class="option-text">${escapeHtml(option.label)} <span class="option-count">${formatInt.format(option.count)}</span></span>
        </label>
      `).join("");
      node.innerHTML = html;
      updateCaptions();
    }

    function updateCaptions() {
      $("#date-caption").textContent = dateCaption(state.draft);
      for (const key of Object.keys(optionDefs)) {
        $(`#${key}-caption`).textContent = selectedCaption(state.draft[key], options[key].length);
      }
    }

    function dateCaption(filters) {
      if (!filters.from && !filters.to) return "2026";
      return `${filters.from || "2026-01-01"} - ${filters.to || "2026-12-31"}`;
    }

    function markDirty() {
      $("#filters").classList.add("dirty");
      updateCaptions();
    }

    function clearDirty() {
      $("#filters").classList.remove("dirty");
    }

    function applyFiltersNow() {
      const filters = state.applied;
      const from = filters.from;
      const to = filters.to;
      const result = [];
      for (const row of records) {
        if (from && row.date < from) continue;
        if (to && row.date > to) continue;
        if (filters.developers.size && !filters.developers.has(row.developerId)) continue;
        if (filters.objects.size && !filters.objects.has(row.objectId)) continue;
        if (filters.districts.size && !filters.districts.has(row.districtKey)) continue;
        if (filters.purchases.size && !filters.purchases.has(row.purchaseKey)) continue;
        if (filters.lenders.size && !filters.lenders.has(row.lenderKey)) continue;
        result.push(row);
      }
      return result;
    }

    function scheduleRender() {
      const token = ++state.renderToken;
      document.body.classList.add("busy");
      $("#apply-btn").disabled = true;
      $("#apply-btn").textContent = "Применяется";
      requestAnimationFrame(() => {
        if (token !== state.renderToken) return;
        const started = performance.now();
        state.filtered = applyFiltersNow();
        state.sorted = sortedByDate(state.filtered);
        state.tablePage = 1;
        renderDashboard(started);
      });
    }

    function renderDashboard(started) {
      const rows = state.filtered;
      renderKpi(rows);
      renderBarChart("chart-developers", aggregate(rows, "developerId", "developer"), 20);
      renderBarChart("chart-objects", aggregate(rows, "objectId", "object"), 20);
      renderBarChart("chart-districts", aggregate(rows, "districtKey", "district"), 14);
      renderBarChart("chart-purchase", aggregate(rows, "purchaseKey", "purchase"), 8);
      renderMonthChart(rows);
      renderBarChart("chart-lenders", aggregate(rows, "lenderKey", "lender"), 16);
      renderTable();
      const elapsed = performance.now() - started;
      window.__DASHBOARD_RENDER_PERF__ = { lastMs: elapsed, rows: rows.length };
      $("#status").innerHTML = `<strong>${formatInt.format(rows.length)}</strong> сделок · обновлено за ${elapsed.toFixed(1)} мс`;
      document.body.classList.remove("busy");
      $("#apply-btn").disabled = false;
      $("#apply-btn").textContent = "Применить";
      clearDirty();
    }

    function renderKpi(rows) {
      $("#kpi-count").textContent = formatInt.format(rows.length);
      $("#kpi-note").textContent = `из ${formatInt.format(records.length)} сделок в базе`;
      $("#developers-subtitle").textContent = "топ-20";
      $("#objects-subtitle").textContent = "топ-20";
      $("#districts-subtitle").textContent = "по всем районам";
      $("#purchase-subtitle").textContent = "по типу";
      $("#months-subtitle").textContent = "2026";
      $("#lenders-subtitle").textContent = "топ-16";
    }

    function aggregate(rows, keyField, labelField) {
      const map = new Map();
      for (const row of rows) {
        const key = row[keyField] || EMPTY_KEY;
        if (!map.has(key)) map.set(key, { key, label: row[labelField] || "(не указан)", count: 0 });
        map.get(key).count += 1;
      }
      return Array.from(map.values()).sort((a, b) => b.count - a.count || a.label.localeCompare(b.label, "ru"));
    }

    function renderBarChart(id, items, limit) {
      const node = document.getElementById(id);
      if (!items.length) {
        node.innerHTML = `<div class="empty">Нет данных</div>`;
        return;
      }
      const top = items.slice(0, limit);
      const max = Math.max(...top.map((item) => item.count), 1);
      node.innerHTML = `<div class="bar-list">${top.map((item) => `
        <div class="bar-row">
          <div class="bar-label" title="${escapeHtml(item.label)}">${escapeHtml(item.label)}</div>
          <div class="bar-track"><div class="bar-fill" style="width:${(item.count / max * 100).toFixed(2)}%"></div></div>
          <div class="bar-value">${formatInt.format(item.count)}</div>
        </div>
      `).join("")}</div>`;
    }

    function renderMonthChart(rows) {
      const counts = Array(12).fill(0);
      for (const row of rows) {
        const monthIndex = Number(row.date.slice(5, 7)) - 1;
        if (monthIndex >= 0 && monthIndex < 12) counts[monthIndex] += 1;
      }
      const max = Math.max(...counts, 1);
      $("#chart-months").innerHTML = `<div class="month-grid">${counts.map((count, index) => `
        <div class="month-col">
          <div class="month-bar-wrap"><div class="month-bar" style="height:${Math.max(2, count / max * 100).toFixed(2)}%"></div></div>
          <div class="month-value">${formatInt.format(count)}</div>
          <div class="month-label">${MONTHS[index]}</div>
        </div>
      `).join("")}</div>`;
    }

    function tableRows() {
      const query = normalize(state.tableQuery);
      const rows = query ? state.sorted.filter((row) => row.search.includes(query)) : state.sorted;
      return rows;
    }

    function sortedByDate(rows) {
      return rows.slice().sort((a, b) => (b.dateNum - a.dateNum) || a.developer.localeCompare(b.developer, "ru"));
    }

    function renderTable() {
      const rows = tableRows();
      const pages = Math.max(1, Math.ceil(rows.length / PAGE_SIZE));
      state.tablePage = Math.min(state.tablePage, pages);
      const start = (state.tablePage - 1) * PAGE_SIZE;
      const pageRows = rows.slice(start, start + PAGE_SIZE);
      $("#deal-rows").innerHTML = pageRows.map((row) => `
        <tr>
          <td>${escapeHtml(row.date)}</td>
          <td>${escapeHtml(row.developer)}</td>
          <td>${escapeHtml(row.object)}</td>
          <td>${escapeHtml(row.district)}</td>
          <td>${escapeHtml(row.purchase)}</td>
          <td>${escapeHtml(row.lender)}</td>
          <td class="num">${row.area ? formatArea.format(row.area) : ""}</td>
          <td class="num">${row.amount ? formatMoney.format(row.amount) : ""}</td>
        </tr>
      `).join("");
      $("#table-status").textContent = `${formatInt.format(rows.length)} сделок · страница ${formatInt.format(state.tablePage)} из ${formatInt.format(pages)}`;
      $("#prev-page").disabled = state.tablePage <= 1;
      $("#next-page").disabled = state.tablePage >= pages;
    }

    function escapeHtml(value) {
      return String(value ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
    }

    function setDateRange(from, to) {
      state.draft.from = from;
      state.draft.to = to;
      $("#date-from").value = from;
      $("#date-to").value = to;
      markDirty();
    }

    function initEvents() {
      $("#date-from").addEventListener("change", (event) => {
        state.draft.from = clampDate(event.target.value);
        event.target.value = state.draft.from;
        markDirty();
      });
      $("#date-to").addEventListener("change", (event) => {
        state.draft.to = clampDate(event.target.value);
        event.target.value = state.draft.to;
        markDirty();
      });
      document.querySelector(".quick-buttons").addEventListener("click", (event) => {
        const range = event.target.dataset.range;
        if (!range) return;
        const ranges = {
          all: ["", ""],
          q1: ["2026-01-01", "2026-03-31"],
          q2: ["2026-04-01", "2026-06-30"],
          jan: ["2026-01-01", "2026-01-31"],
          feb: ["2026-02-01", "2026-02-28"],
          mar: ["2026-03-01", "2026-03-31"]
        };
        setDateRange(...ranges[range]);
      });
      $("#apply-btn").addEventListener("click", () => {
        state.applied = cloneFilters(state.draft);
        scheduleRender();
      });
      $("#reset-btn").addEventListener("click", () => {
        state.draft = blankFilters();
        state.applied = blankFilters();
        $("#date-from").value = "";
        $("#date-to").value = "";
        Object.keys(optionDefs).forEach((key) => {
          optionDefs[key].search = "";
          const search = document.querySelector(`[data-option-search="${key}"]`);
          if (search) search.value = "";
          renderOptions(key);
        });
        scheduleRender();
      });
      let tableTimer = 0;
      $("#table-search").addEventListener("input", (event) => {
        window.clearTimeout(tableTimer);
        tableTimer = window.setTimeout(() => {
          state.tableQuery = event.target.value;
          state.tablePage = 1;
          renderTable();
        }, 120);
      });
      $("#prev-page").addEventListener("click", () => {
        state.tablePage = Math.max(1, state.tablePage - 1);
        renderTable();
      });
      $("#next-page").addEventListener("click", () => {
        state.tablePage += 1;
        renderTable();
      });
      $("#export-btn").addEventListener("click", exportCsv);
    }

    function exportCsv() {
      const rows = tableRows();
      const header = ["Дата", "Застройщик", "Объект", "Район", "Способ покупки", "Банк", "Площадь", "Цена сделки"];
      const lines = [header, ...rows.map((row) => [row.date, row.developer, row.object, row.district, row.purchase, row.lender, row.area, row.amount])]
        .map((line) => line.map(csvCell).join(";"));
      const blob = new Blob(["\\ufeff" + lines.join("\\n")], { type: "text/csv;charset=utf-8" });
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = "deals-2026.csv";
      link.click();
      URL.revokeObjectURL(link.href);
    }

    function csvCell(value) {
      return `"${String(value ?? "").replace(/"/g, '""')}"`;
    }

    function boot() {
      renderFilterHost();
      initEvents();
      const started = performance.now();
      state.filtered = records;
      state.sorted = sortedByDate(records);
      renderDashboard(started);
      const bootMs = performance.now() - tBoot;
      $("#status").innerHTML = `<strong>${formatInt.format(records.length)}</strong> сделок · старт за ${bootMs.toFixed(1)} мс`;
      window.__DASHBOARD_BOOT__ = { bootMs, rows: records.length };
    }

    boot();
  </script>
</body>
</html>
"""


def main() -> None:
    data_payload = DATA_JSON_PATH.read_text(encoding="utf-8")
    summary_payload = SUMMARY_JSON_PATH.read_text(encoding="utf-8") if SUMMARY_JSON_PATH.exists() else "{}"
    json.loads(data_payload)
    json.loads(summary_payload)
    html = (
        HTML_TEMPLATE.replace("__DASHBOARD_DATA_JSON__", safe_json_for_script(data_payload))
        .replace("__SUMMARY_JSON__", safe_json_for_script(summary_payload))
    )
    HTML_PATH.write_text(html, encoding="utf-8")
    print(
        json.dumps(
            {
                "html": HTML_PATH.name,
                "html_size_mb": round(HTML_PATH.stat().st_size / (1024 * 1024), 2),
                "data_size_mb": round(DATA_JSON_PATH.stat().st_size / (1024 * 1024), 2),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
