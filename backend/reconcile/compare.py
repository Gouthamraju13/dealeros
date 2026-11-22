"""The comparison rules. Plain Python only: no database, no web code, so it is easy to test.

Input
  a_rows: {record_id: {"total": Decimal|None, "location": str, "date": date|None, "state": str}}
  b_rows: [{"entry_id", "ref" (already cleaned, may be None), "value": Decimal|None,
            "location": str, "date": date|None}]

Output: a list of dicts, one per disagreement, each with
  reason, record_id, a_value, b_value, a_location, b_location, a_date, b_date, entry_ids
"""
from decimal import Decimal

MISSING_IN_B = "MISSING_IN_B"
ORPHAN_IN_B = "ORPHAN_IN_B"
DUPLICATE_IN_B = "DUPLICATE_IN_B"
VALUE_MISMATCH = "VALUE_MISMATCH"
LOCATION_MISMATCH = "LOCATION_MISMATCH"  # extra
DATE_MISMATCH = "DATE_MISMATCH"  # extra
VOIDED_IN_A = "VOIDED_IN_A"  # extra: A says VOIDED but B still holds an entry

ALL_REASONS = [
    MISSING_IN_B, ORPHAN_IN_B, DUPLICATE_IN_B, VALUE_MISMATCH,
    LOCATION_MISMATCH, DATE_MISMATCH, VOIDED_IN_A,
]


def _row(reason, record_id, a=None, entries=(), b_value=None):
    """Build one result dict. `a` is the A record (or None for an orphan)."""
    return {
        "reason": reason,
        "record_id": record_id,
        "a_value": a["total"] if a else None,
        "b_value": b_value,
        "a_location": a["location"] if a else "",
        "b_location": entries[0]["location"] if entries else "",
        "a_date": a["date"] if a else None,
        "b_date": entries[0]["date"] if entries else None,
        "entry_ids": [e["entry_id"] for e in entries],
    }


def _sum_known(values):
    """Add up the values we know. None if we know none of them (unknown is not zero)."""
    known = [v for v in values if v is not None]
    return sum(known, Decimal("0")) if known else None


def compare(a_rows, b_rows):
    out = []

    # Group B's entries by their cleaned reference.
    by_ref = {}
    for e in b_rows:
        by_ref.setdefault(e["ref"], []).append(e)

    # 1. Orphans: B points at a record that A does not have (or at nothing readable).
    for ref, entries in by_ref.items():
        if ref is None or ref not in a_rows:
            for e in entries:
                out.append(_row(ORPHAN_IN_B, ref or e["entry_id"], None, [e], e["value"]))

    # 2. Walk through every A record.
    for rid, a in a_rows.items():
        entries = by_ref.get(rid, [])
        voided = (a.get("state") or "").upper() == "VOIDED"

        if voided:
            # A voided record is meant to be gone. No B entry is fine; an entry is a disagreement.
            if entries:
                out.append(_row(VOIDED_IN_A, rid, a, entries, _sum_known(e["value"] for e in entries)))
            continue

        if not entries:
            out.append(_row(MISSING_IN_B, rid, a))
            continue

        values = [e["value"] for e in entries]

        if len(entries) > 1:
            if any(v is None for v in values):
                out.append(_row(VALUE_MISMATCH, rid, a, entries, _sum_known(values)))
            elif sum(values, Decimal("0")) != a["total"]:
                # Parts that add up exactly to A's total are a split: NOT an error.
                out.append(_row(DUPLICATE_IN_B, rid, a, entries, sum(values, Decimal("0"))))
            continue

        e = entries[0]
        if e["value"] is None or e["value"] != a["total"]:
            out.append(_row(VALUE_MISMATCH, rid, a, entries, e["value"]))
        if e["location"] != a["location"]:
            out.append(_row(LOCATION_MISMATCH, rid, a, entries, e["value"]))
        if e["date"] != a["date"]:
            out.append(_row(DATE_MISMATCH, rid, a, entries, e["value"]))

    return out