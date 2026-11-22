"""Reads the three CSV files into the database without losing a single row.

The rule: every CSV row becomes exactly one database row, even a messy one.
If a field cannot be understood we store NULL and keep the original text.
We never skip a row and we never turn a bad value into 0.
"""
import csv
import logging
import re
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from .models import Location, SystemARecord, SystemBEntry

log = logging.getLogger(__name__)


# ---------- small cleaning helpers (pure functions, easy to test) ----------

def normalize_ref(raw):
    """'rec1034', ' REC - 1070 ', '1112' -> 'REC-1034', 'REC-1070', 'REC-1112'.

    Returns None when there are no digits at all.
    """
    m = re.search(r"\d+", raw or "")
    return f"REC-{m.group()}" if m else None


def parse_amount(raw):
    """'1,25,400.00' -> Decimal('125400.00'). Blank or junk -> None (unknown), never 0."""
    s = (raw or "").strip().replace(",", "")
    if not s:
        return None
    try:
        value = Decimal(s)
    except InvalidOperation:
        return None
    return value if value.is_finite() else None


def parse_date(raw):
    """'2026-03-24' -> date. Anything else -> None (the raw text is kept elsewhere)."""
    try:
        return date.fromisoformat((raw or "").strip())
    except ValueError:
        return None


def clean_text(raw):
    return (raw or "").strip()


def read_rows(path):
    """Read a CSV as plain text (nothing auto-converted) with every cell stripped."""
    # utf-8-sig quietly removes a BOM if Excel added one.
    with open(path, newline="", encoding="utf-8-sig") as f:
        return [{(k or "").strip(): clean_text(v) for k, v in row.items()} for row in csv.DictReader(f)]


# ---------- the importer ----------

def import_all(data_dir):
    """Import the three CSVs. Safe to run again: update_or_create means no duplicates."""
    data_dir = Path(data_dir)
    stats = {
        "locations_read": 0, "locations_saved": 0,
        "a_read": 0, "a_saved": 0, "a_actor_blank": 0, "a_amounts_unreadable": 0,
        "b_read": 0, "b_saved": 0, "b_values_empty": 0, "b_refs_cleaned": 0,
        "problems": [],
    }

    locs = {}
    for row in read_rows(data_dir / "locations.csv"):
        stats["locations_read"] += 1
        loc, _ = Location.objects.update_or_create(
            location_id=row["location_id"],
            defaults={"org_id": row["org_id"], "name": row.get("location_name", "")},
        )
        locs[loc.location_id] = loc
        stats["locations_saved"] += 1

    for row in read_rows(data_dir / "system_a.csv"):
        stats["a_read"] += 1
        rid = row["record_id"]
        if not row.get("actor_id"):
            stats["a_actor_blank"] += 1
        amounts = {k: parse_amount(row.get(k)) for k in ("base_value", "adjustment", "total_value")}
        if any(v is None for v in amounts.values()):
            stats["a_amounts_unreadable"] += 1
            stats["problems"].append(f"A {rid}: an amount could not be read, stored as NULL")
        if row["location_id"] not in locs:
            stats["problems"].append(f"A {rid}: unknown location {row['location_id']!r}")
        SystemARecord.objects.update_or_create(
            record_id=rid,
            defaults={
                "location": locs.get(row["location_id"]),
                "location_raw": row["location_id"],
                "event_date": parse_date(row["event_date"]),
                "event_date_raw": row["event_date"],
                "category_code": row.get("category_code", ""),
                "actor_id": row.get("actor_id") or None,  # empty text -> NULL
                **amounts,
                "state": row.get("state", ""),
            },
        )
        stats["a_saved"] += 1

    for row in read_rows(data_dir / "system_b.csv"):
        stats["b_read"] += 1
        eid = row["entry_id"]
        ref_raw = row["record_ref"]
        ref = normalize_ref(ref_raw)
        if ref != ref_raw:
            stats["b_refs_cleaned"] += 1
        if ref is None:
            stats["problems"].append(f"B {eid}: reference {ref_raw!r} has no digits")
        value = parse_amount(row["value"])
        if value is None:
            stats["b_values_empty"] += 1
            stats["problems"].append(f"B {eid}: value {row['value']!r} stored as NULL (unknown, not 0)")
        if row["location_id"] not in locs:
            stats["problems"].append(f"B {eid}: unknown location {row['location_id']!r}")
        SystemBEntry.objects.update_or_create(
            entry_id=eid,
            defaults={
                "record_ref_raw": ref_raw,
                "record_ref": ref,
                "location": locs.get(row["location_id"]),
                "location_raw": row["location_id"],
                "recorded_on": parse_date(row["recorded_on"]),
                "recorded_on_raw": row["recorded_on"],
                "value_raw": row["value"],
                "value": value,
                "label": row.get("label", ""),
            },
        )
        stats["b_saved"] += 1

    # The safety net: what is really in the database must match what we read.
    stats["a_in_db"] = SystemARecord.objects.count()
    stats["b_in_db"] = SystemBEntry.objects.count()
    return stats


def summary_line(s):
    return (
        f"A: {s['a_read']} read, {s['a_saved']} saved, {s['a_in_db']} in database; "
        f"B: {s['b_read']} read, {s['b_saved']} saved, {s['b_in_db']} in database; "
        f"values left empty: {s['b_values_empty']}; refs cleaned: {s['b_refs_cleaned']}; "
        f"A actor_id blank: {s['a_actor_blank']}"
    )