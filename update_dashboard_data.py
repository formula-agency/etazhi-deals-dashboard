from __future__ import annotations

import datetime as dt
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
DATA_PATH = ROOT / "OLD_DATA" / "Тюмень_Сделки_Экспозиция_25_06_2026.xlsx"
DATA_MARKER = '<script id="dashboard-data" type="application/json">'

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
    start = html.index(DATA_MARKER) + len(DATA_MARKER)
    end = html.index("</script>", start)
    return json.loads(html[start:end])


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
            "deal_area_abs_diff_sqm": area_abs_diff,
            "deal_area_rel_diff": area_rel_diff,
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


def replace_dashboard_data(data: dict[str, Any]) -> None:
    html = HTML_PATH.read_text(encoding="utf-8")
    start = html.index(DATA_MARKER) + len(DATA_MARKER)
    end = html.index("</script>", start)
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    HTML_PATH.write_text(html[:start] + payload + html[end:], encoding="utf-8")


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
    }


def main() -> None:
    current = parse_current_dashboard()
    source_rows = load_deal_rows()
    selected_rows = choose_rows(source_rows)
    data = build_dashboard_data(current, selected_rows)
    replace_dashboard_data(data)
    print(json.dumps(summarize(data, len(source_rows)), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
