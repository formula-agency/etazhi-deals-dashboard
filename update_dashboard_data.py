from __future__ import annotations

import datetime as dt
import gzip
import hashlib
import json
import math
import re
from collections import OrderedDict, defaultdict
from pathlib import Path
from typing import Any

import openpyxl


ROOT = Path(__file__).resolve().parent
HTML_PATH = ROOT / "index.html"
DATA_JSON_PATH = ROOT / "dashboard-data.json"
DATA_JSON_GZIP_PATH = ROOT / "dashboard-data.json.gz"
SUMMARY_JSON_PATH = ROOT / "dashboard-summary.json"
DATA_PATH = ROOT / "OLD_DATA" / "Тюмень_Сделки_Экспозиция_25_06_2026.xlsx"
DATA_MARKER = '<script id="dashboard-data" type="application/json">'
DEAL_FIELDS = [
    "deal_id",
    "developer_id",
    "developer_name",
    "developer_group_id",
    "developer_group_name",
    "object_id",
    "object_name",
    "object_group_id",
    "object_group_name",
    "district_name",
    "contract_number",
    "contract_date",
    "deal_area_sqm",
    "deal_area_egrn_sqm",
    "deal_area_linked_sqm",
    "deal_area_source",
    "deal_area_abs_diff_sqm",
    "deal_area_rel_diff",
    "deal_area_suspicious",
    "deal_area_issue_reason",
    "deal_area_bin",
    "deal_amount",
    "deal_amount_effective",
    "deal_amount_contract",
    "deal_amount_expo",
    "deal_amount_donor",
    "deal_amount_source",
    "deal_amount_contract_rejected_high_ppsm",
    "deal_amount_contract_rejected_low_ppsm",
    "purchase_type_raw",
    "buyer_type_raw",
    "mortgage_lender_raw",
]
STRING_DICTIONARY_FIELDS = {
    "developer_id",
    "developer_name",
    "developer_group_id",
    "developer_group_name",
    "object_id",
    "object_name",
    "object_group_id",
    "object_group_name",
    "district_name",
    "contract_number",
    "contract_date",
    "deal_area_source",
    "deal_area_issue_reason",
    "deal_area_bin",
    "deal_amount_source",
    "purchase_type_raw",
    "buyer_type_raw",
    "mortgage_lender_raw",
}
BOOLEAN_FIELDS = {
    "deal_area_suspicious",
    "deal_amount_contract_rejected_high_ppsm",
    "deal_amount_contract_rejected_low_ppsm",
}
SUMMARY_DETAIL_FIELDS = [
    "deal_id",
    "developer_name",
    "developer_group_name",
    "object_name",
    "object_group_name",
    "contract_number",
    "contract_date",
    "deal_area_sqm",
    "deal_amount",
    "deal_amount_contract",
    "deal_amount_source",
    "deal_area_issue_reason",
]

AREA_BINS = [
    (0, 30, "(0,30]"),
    (30, 42, "(30,42]"),
    (42, 51, "(42,51]"),
    (51, 60, "(51,60]"),
    (60, 81, "(60,81]"),
]


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).replace("\xa0", " ").strip()


def key_text(value: Any) -> str:
    return re.sub(r"\s+", " ", clean_text(value)).lower()


def stable_hash(value: Any, length: int) -> str:
    text = key_text(value) or "unknown"
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:length]


def group_id(prefix: str, value: Any) -> str:
    return f"{prefix}-{stable_hash(value, 12)}"


def synthetic_id(value: Any) -> str:
    return stable_hash(value, 16)


def to_number(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, bool):
        return 0.0
    if isinstance(value, (int, float)):
        if not math.isfinite(float(value)):
            return 0.0
        return float(value)
    text = clean_text(value)
    if not text:
        return 0.0
    text = text.replace(" ", "").replace(",", ".")
    text = re.sub(r"[^0-9.\-]", "", text)
    if not text or text in {"-", ".", "-."}:
        return 0.0
    try:
        value_float = float(text)
    except ValueError:
        return 0.0
    return value_float if math.isfinite(value_float) else 0.0


def number_value(value: Any) -> int | float:
    numeric = to_number(value)
    rounded = round(numeric)
    if abs(numeric - rounded) < 1e-9:
        return int(rounded)
    return numeric


def date_iso(value: Any) -> str:
    if isinstance(value, dt.datetime):
        return value.date().isoformat()
    if isinstance(value, dt.date):
        return value.isoformat()
    text = clean_text(value)
    if not text:
        return ""
    if re.match(r"^\d{4}-\d{2}-\d{2}", text):
        return text[:10]
    if re.match(r"^\d{2}\.\d{2}\.\d{4}", text):
        day, month, year = text[:10].split(".")
        return f"{year}-{month}-{day}"
    return text[:10]


def area_bin(area: float) -> str:
    if area <= 0:
        return "unknown"
    for low, high, label in AREA_BINS:
        if area > low and area <= high:
            return label
    return "(81,+inf]"


def parse_current_dashboard() -> dict[str, Any]:
    html = HTML_PATH.read_text(encoding="utf-8")
    if DATA_MARKER in html:
        start = html.index(DATA_MARKER) + len(DATA_MARKER)
        end = html.index("</script>", start)
        return json.loads(html[start:end])
    if DATA_JSON_PATH.exists():
        payload = json.loads(DATA_JSON_PATH.read_text(encoding="utf-8"))
        if "dealRows" in payload and "dealFields" in payload:
            return inflate_compact_dashboard_data(payload)
        return payload
    return {"deals": [], "developers": [], "objects": [], "districts": []}


def inflate_compact_dashboard_data(payload: dict[str, Any]) -> dict[str, Any]:
    fields = list(payload.get("dealFields", []))
    rows = payload.get("dealRows", [])
    string_table = payload.get("stringTable", [])
    string_field_indexes = set(payload.get("stringFieldIndexes", []))
    boolean_field_indexes = set(payload.get("booleanFieldIndexes", []))

    deals = []
    for values in rows:
        deal = {}
        for index, field in enumerate(fields):
            value = values[index] if index < len(values) else None
            if index in string_field_indexes:
                if isinstance(value, int) and 0 <= value < len(string_table):
                    value = string_table[value]
                elif value is None:
                    value = ""
            elif index in boolean_field_indexes:
                value = bool(value)
            deal[field] = value
        deals.append(deal)

    return {
        "deals": deals,
        "developers": payload.get("developers", []),
        "objects": payload.get("objects", []),
        "districts": payload.get("districts", []),
    }


def row_dict(headers: list[str], values: tuple[Any, ...]) -> dict[str, Any]:
    return {header: values[index] for index, header in enumerate(headers) if header}


def duplicate_score(row: dict[str, Any]) -> tuple[int, int, float, float, float, int]:
    match_type = key_text(row.get("Тип сцепки с экспозицией"))
    if "полное" in match_type:
        match_score = 40
    elif "частич" in match_type:
        match_score = 30
    elif "нет совпад" in match_type:
        match_score = 0
    else:
        match_score = 10

    return (
        1 if clean_text(row.get("id сцепленного объекта")) else 0,
        match_score,
        to_number(row.get("Ориентировочная цена объекта")),
        to_number(row.get("Площадь сцепленного объекта (Экспозиция)")),
        to_number(row.get("Цена объекта по договору")),
        1 if clean_text(row.get("Номер договора")) else 0,
    )


def choose_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: OrderedDict[str, list[dict[str, Any]]] = OrderedDict()
    for row in rows:
        deal_id = clean_text(row.get("id сделки"))
        if not deal_id:
            continue
        grouped.setdefault(deal_id, []).append(row)
    return [max(items, key=duplicate_score) for items in grouped.values()]


def same_number(left: Any, right: Any) -> bool:
    return abs(to_number(left) - to_number(right)) < 0.01


def build_price_fields(row: dict[str, Any], old_row: dict[str, Any] | None) -> dict[str, Any]:
    contract = number_value(row.get("Цена объекта по договору"))
    expo = number_value(row.get("Ориентировочная цена объекта"))
    area = to_number(row.get("Площадь из ЕГРН"))

    if old_row:
        same_core = (
            date_iso(row.get("Дата договора")) == clean_text(old_row.get("contract_date"))
            and same_number(row.get("Цена объекта по договору"), old_row.get("deal_amount_contract"))
            and same_number(row.get("Ориентировочная цена объекта"), old_row.get("deal_amount_expo"))
            and same_number(area, old_row.get("deal_area_egrn_sqm"))
        )
        if same_core:
            return {
                "deal_amount": number_value(old_row.get("deal_amount")),
                "deal_amount_effective": number_value(old_row.get("deal_amount_effective")),
                "deal_amount_contract": number_value(old_row.get("deal_amount_contract")),
                "deal_amount_expo": number_value(old_row.get("deal_amount_expo")),
                "deal_amount_donor": number_value(old_row.get("deal_amount_donor")),
                "deal_amount_source": clean_text(old_row.get("deal_amount_source")) or "missing",
                "deal_amount_contract_rejected_high_ppsm": bool(
                    old_row.get("deal_amount_contract_rejected_high_ppsm")
                ),
                "deal_amount_contract_rejected_low_ppsm": bool(
                    old_row.get("deal_amount_contract_rejected_low_ppsm")
                ),
            }

    if to_number(contract) > 0:
        effective = contract
        source = "contract"
    elif to_number(expo) > 0:
        effective = expo
        source = "expo"
    else:
        effective = 0
        source = "missing"

    return {
        "deal_amount": effective,
        "deal_amount_effective": effective,
        "deal_amount_contract": contract,
        "deal_amount_expo": expo,
        "deal_amount_donor": 0,
        "deal_amount_source": source,
        "deal_amount_contract_rejected_high_ppsm": False,
        "deal_amount_contract_rejected_low_ppsm": False,
    }


def build_dashboard_data(current: dict[str, Any], selected_rows: list[dict[str, Any]]) -> dict[str, Any]:
    old_by_deal_id = {clean_text(row.get("deal_id")): row for row in current.get("deals", [])}
    old_developer_by_object = {
        clean_text(row.get("object_id")): clean_text(row.get("developer_id"))
        for row in current.get("deals", [])
        if clean_text(row.get("object_id")) and clean_text(row.get("developer_id"))
    }

    deals: list[dict[str, Any]] = []
    developers: dict[str, dict[str, Any]] = {}
    objects: dict[str, dict[str, Any]] = {}
    districts: set[str] = set()

    for row in selected_rows:
        deal_id = clean_text(row.get("id сделки"))
        developer_name = clean_text(row.get("Девелопер")) or "Не указано"
        builder_name = clean_text(row.get("Застройщик")) or developer_name
        object_name = clean_text(row.get("Название ЖК")) or "Не указано"
        object_id = clean_text(row.get("id корпуса")) or synthetic_id(f"{object_name}|{builder_name}")
        developer_id = old_developer_by_object.get(object_id) or synthetic_id(builder_name)

        dev_group_id = group_id("devgrp", developer_name)
        obj_group_id = group_id("objgrp", object_name)
        district_name = clean_text(row.get("Район"))
        if district_name:
            districts.add(district_name)

        area_egrn = to_number(row.get("Площадь из ЕГРН"))
        area_linked = to_number(row.get("Площадь сцепленного объекта (Экспозиция)"))
        deal_area = area_egrn if area_egrn > 0 else 0.0
        if area_egrn > 0 and area_linked > 0:
            area_abs_diff = abs(area_egrn - area_linked)
            area_rel_diff = area_abs_diff / area_egrn
        else:
            area_abs_diff = 0.0
            area_rel_diff = 0.0

        if deal_area <= 0:
            area_source = "missing"
            area_suspicious = True
            area_issue_reason = "missing_or_nonpositive"
        elif area_rel_diff > 0.05:
            area_source = "egrn"
            area_suspicious = True
            area_issue_reason = "source_conflict"
        else:
            area_source = "egrn"
            area_suspicious = False
            area_issue_reason = "none"

        price_fields = build_price_fields(row, old_by_deal_id.get(deal_id))

        deal = {
            "deal_id": deal_id,
            "developer_id": developer_id,
            "developer_name": developer_name,
            "developer_group_id": dev_group_id,
            "developer_group_name": developer_name,
            "object_id": object_id,
            "object_name": object_name,
            "object_group_id": obj_group_id,
            "object_group_name": object_name,
            "district_name": district_name,
            "contract_number": clean_text(row.get("Номер договора")),
            "contract_date": date_iso(row.get("Дата договора")),
            "deal_area_sqm": number_value(deal_area),
            "deal_area_egrn_sqm": number_value(area_egrn),
            "deal_area_linked_sqm": number_value(area_linked),
            "deal_area_source": area_source,
            "deal_area_abs_diff_sqm": round(area_abs_diff, 4),
            "deal_area_rel_diff": round(area_rel_diff, 6),
            "deal_area_suspicious": area_suspicious,
            "deal_area_issue_reason": area_issue_reason,
            "deal_area_bin": area_bin(deal_area),
            **price_fields,
            "purchase_type_raw": clean_text(row.get("Тип покупки")),
            "buyer_type_raw": clean_text(row.get("Тип покупателя")),
            "mortgage_lender_raw": clean_text(row.get("Залогодержатель/Банк")),
        }
        deals.append(deal)

        developers.setdefault(
            dev_group_id,
            {"id": dev_group_id, "name": developer_name, "ids": set()},
        )["ids"].add(developer_id)
        objects.setdefault(
            obj_group_id,
            {"id": obj_group_id, "name": object_name, "ids": set()},
        )["ids"].add(object_id)

    developer_options = sorted(developers.values(), key=lambda item: key_text(item["name"]))
    object_options = sorted(objects.values(), key=lambda item: key_text(item["name"]))
    for item in developer_options + object_options:
        item["ids"] = sorted(item["ids"])

    return {
        "deals": deals,
        "developers": developer_options,
        "objects": object_options,
        "districts": [{"id": name, "name": name} for name in sorted(districts, key=key_text)],
    }


def load_deal_rows() -> list[dict[str, Any]]:
    workbook = openpyxl.load_workbook(DATA_PATH, read_only=True, data_only=True)
    worksheet = workbook["Сделки"]
    iterator = worksheet.iter_rows(values_only=True)
    headers = [clean_text(value) for value in next(iterator)]
    return [row_dict(headers, row) for row in iterator]


def compact_dashboard_data(data: dict[str, Any]) -> dict[str, Any]:
    string_table: list[str] = []
    string_index: dict[str, int] = {}
    string_field_indexes = [
        index
        for index, field in enumerate(DEAL_FIELDS)
        if field in STRING_DICTIONARY_FIELDS
    ]
    boolean_field_indexes = [
        index
        for index, field in enumerate(DEAL_FIELDS)
        if field in BOOLEAN_FIELDS
    ]
    string_field_index_set = set(string_field_indexes)
    boolean_field_index_set = set(boolean_field_indexes)

    def string_token(value: Any) -> int:
        text = clean_text(value)
        token = string_index.get(text)
        if token is not None:
            return token
        token = len(string_table)
        string_index[text] = token
        string_table.append(text)
        return token

    deal_rows = []
    for row in data["deals"]:
        values = []
        for index, field in enumerate(DEAL_FIELDS):
            value = row.get(field)
            if index in string_field_index_set:
                values.append(string_token(value))
            elif index in boolean_field_index_set:
                values.append(1 if value else 0)
            else:
                values.append(value)
        deal_rows.append(values)

    return {
        "version": 2,
        "dealFields": DEAL_FIELDS,
        "dealRows": deal_rows,
        "stringTable": string_table,
        "stringFieldIndexes": string_field_indexes,
        "booleanFieldIndexes": boolean_field_indexes,
        "developers": data["developers"],
        "objects": data["objects"],
        "districts": data["districts"],
    }


def safe_rate(total_amount: float, total_area: float) -> float:
    return total_amount / total_area if total_area else 0.0


def kpi_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    sales_amount = 0.0
    total_area = 0.0
    clean_sales_amount = 0.0
    clean_total_area = 0.0
    area_issue_count = 0
    area_conflict_count = 0

    for row in rows:
        amount = to_number(row.get("deal_amount"))
        area = max(0.0, to_number(row.get("deal_area_sqm")))
        has_conflict = clean_text(row.get("deal_area_issue_reason")) == "source_conflict"
        sales_amount += amount
        total_area += area
        if row.get("deal_area_suspicious"):
            area_issue_count += 1
        if has_conflict:
            area_conflict_count += 1
        else:
            clean_sales_amount += amount
            clean_total_area += area

    count = len(rows)
    rate = safe_rate(sales_amount, total_area)
    clean_rate = safe_rate(clean_sales_amount, clean_total_area)
    impact_percent = ((clean_rate - rate) / rate) * 100 if rate else 0.0
    return {
        "count": count,
        "sales": round(sales_amount),
        "avg": round(sales_amount / count) if count else 0,
        "area": round(total_area, 1),
        "rate": round(rate),
        "areaIssueCount": area_issue_count,
        "areaConflictCount": area_conflict_count,
        "cleanRate": round(clean_rate),
        "impactPercent": round(impact_percent, 1),
    }


def aggregate_summary(
    rows: list[dict[str, Any]], id_key: str, label_key: str, top_n: int = 10
) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for row in rows:
        item_id = clean_text(row.get(id_key)) or "unknown"
        item = grouped.setdefault(
            item_id,
            {"id": item_id, "label": clean_text(row.get(label_key)) or item_id, "amount": 0, "deals": 0, "area": 0.0},
        )
        item["amount"] += to_number(row.get("deal_amount"))
        item["deals"] += 1
        item["area"] += max(0.0, to_number(row.get("deal_area_sqm")))

    ranked = sorted(grouped.values(), key=lambda item: (-item["amount"], key_text(item["label"])))
    return [
        {
            **item,
            "amount": round(item["amount"]),
            "area": round(item["area"], 1),
            "weighted_rate": round(safe_rate(item["amount"], item["area"])),
        }
        for item in ranked[:top_n]
    ]


def pareto_core_summary(
    rows: list[dict[str, Any]], id_key: str, label_key: str, target_share: float = 80.0
) -> dict[str, Any]:
    ranked = aggregate_summary(rows, id_key, label_key, top_n=10_000)
    grand_total = sum(to_number(item.get("amount")) for item in ranked)
    cumulative = 0.0
    core_rows = []
    for item in ranked:
        share = (to_number(item.get("amount")) / grand_total) * 100 if grand_total else 0.0
        cumulative += share
        core_rows.append(
            {
                "id": item["id"],
                "label": item["label"],
                "amount": item["amount"],
                "share": round(share, 1),
                "cumulative": round(min(cumulative, 100.0), 1),
            }
        )
        if cumulative >= target_share:
            break

    total_count = len(ranked)
    core_count = len(core_rows)
    return {
        "rows": core_rows,
        "totalCount": total_count,
        "coreCount": core_count,
        "coreSharePct": round((core_count / total_count) * 100, 1) if total_count else 0,
        "revenueSharePct": core_rows[-1]["cumulative"] if core_rows else 0,
    }


def detail_preview_rows(rows: list[dict[str, Any]], limit: int = 50) -> list[dict[str, Any]]:
    return [
        {field: row.get(field) for field in SUMMARY_DETAIL_FIELDS}
        for row in rows[:limit]
    ]


def summary_dashboard_data(data: dict[str, Any]) -> dict[str, Any]:
    rows = data["deals"]
    return {
        "version": 1,
        "kpi": kpi_summary(rows),
        "developers": data["developers"],
        "objects": data["objects"],
        "districts": data["districts"],
        "topDevelopers": aggregate_summary(
            rows, "developer_group_id", "developer_group_name", top_n=10
        ),
        "topObjects": aggregate_summary(rows, "object_group_id", "object_group_name", top_n=10),
        "coreDevelopers": pareto_core_summary(
            rows, "developer_group_id", "developer_group_name"
        ),
        "coreObjects": pareto_core_summary(rows, "object_group_id", "object_group_name"),
        "detailPreview": {
            "totalRows": len(rows),
            "rows": detail_preview_rows(rows, 50),
        },
    }


def write_dashboard_data(data: dict[str, Any]) -> None:
    payload = json.dumps(compact_dashboard_data(data), ensure_ascii=False, separators=(",", ":"))
    DATA_JSON_PATH.write_text(payload, encoding="utf-8")
    DATA_JSON_GZIP_PATH.write_bytes(gzip.compress(payload.encode("utf-8"), compresslevel=9, mtime=0))
    summary_payload = json.dumps(
        summary_dashboard_data(data),
        ensure_ascii=False,
        separators=(",", ":"),
    )
    SUMMARY_JSON_PATH.write_text(summary_payload, encoding="utf-8")


def summarize(data: dict[str, Any], source_row_count: int) -> dict[str, Any]:
    dates = [row["contract_date"] for row in data["deals"] if row.get("contract_date")]
    sources = defaultdict(int)
    area_issues = defaultdict(int)
    for row in data["deals"]:
        sources[row.get("deal_amount_source", "missing")] += 1
        area_issues[row.get("deal_area_issue_reason", "none")] += 1
    return {
        "source_rows": source_row_count,
        "dashboard_deals": len(data["deals"]),
        "developers": len(data["developers"]),
        "objects": len(data["objects"]),
        "districts": len(data["districts"]),
        "date_min": min(dates) if dates else None,
        "date_max": max(dates) if dates else None,
        "price_sources": dict(sorted(sources.items())),
        "area_issues": dict(sorted(area_issues.items())),
        "html_size_mb": round(HTML_PATH.stat().st_size / (1024 * 1024), 2),
        "data_json_size_mb": round(DATA_JSON_PATH.stat().st_size / (1024 * 1024), 2)
        if DATA_JSON_PATH.exists()
        else None,
        "summary_json_size_kb": round(SUMMARY_JSON_PATH.stat().st_size / 1024, 1)
        if SUMMARY_JSON_PATH.exists()
        else None,
    }


def main() -> None:
    current = parse_current_dashboard()
    source_rows = load_deal_rows()
    selected_rows = choose_rows(source_rows)
    data = build_dashboard_data(current, selected_rows)
    write_dashboard_data(data)
    print(json.dumps(summarize(data, len(source_rows)), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
