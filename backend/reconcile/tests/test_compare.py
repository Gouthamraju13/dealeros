"""Tests for the comparison rules. No database needed: compare() is plain Python."""
from datetime import date
from decimal import Decimal

from reconcile.compare import (
    compare, MISSING_IN_B, ORPHAN_IN_B, DUPLICATE_IN_B, VALUE_MISMATCH,
    LOCATION_MISMATCH, DATE_MISMATCH, VOIDED_IN_A,
)
from reconcile.importer import normalize_ref, parse_amount

D = Decimal


def a_rec(total="100.00", location="LOC-101", when=date(2026, 3, 1), state="CONFIRMED"):
    return {"total": D(total), "location": location, "date": when, "state": state}


def entry(entry_id="E1", ref="REC-1", value="100.00", location="LOC-101", when=date(2026, 3, 1)):
    return {"entry_id": entry_id, "ref": ref, "value": None if value is None else D(value),
            "location": location, "date": when}


def reasons(result):
    return [(r["reason"], r["record_id"]) for r in result]


# ---- one test per kind of disagreement ----

def test_missing_in_b():
    assert reasons(compare({"REC-1": a_rec()}, [])) == [(MISSING_IN_B, "REC-1")]


def test_orphan_in_b():
    result = compare({"REC-1": a_rec()}, [entry(), entry("E9", ref="REC-999", value="5.00")])
    assert reasons(result) == [(ORPHAN_IN_B, "REC-999")]


def test_duplicate_in_b_same_amount_twice():
    result = compare({"REC-1": a_rec()}, [entry("E1"), entry("E2")])
    assert reasons(result) == [(DUPLICATE_IN_B, "REC-1")]
    assert result[0]["b_value"] == D("200.00")  # B holds double what A says


def test_value_mismatch():
    result = compare({"REC-1": a_rec()}, [entry(value="90.00")])
    assert reasons(result) == [(VALUE_MISMATCH, "REC-1")]
    assert result[0]["a_value"] == D("100.00") and result[0]["b_value"] == D("90.00")


def test_blank_value_is_flagged_and_is_not_zero():
    result = compare({"REC-1": a_rec()}, [entry(value=None)])
    assert reasons(result) == [(VALUE_MISMATCH, "REC-1")]
    assert result[0]["b_value"] is None  # unknown, not 0


def test_blank_value_is_flagged_even_when_a_total_is_zero():
    # If blank were treated as 0 this would wrongly look like a perfect match.
    assert reasons(compare({"REC-1": a_rec(total="0.00")}, [entry(value=None)])) == [(VALUE_MISMATCH, "REC-1")]


def test_value_equals_base_instead_of_total_is_flagged():
    # B must match A's total_value (base + adjustment), not base_value.
    a = a_rec(total="121388.01")
    assert reasons(compare({"REC-1": a}, [entry(value="94834.38")])) == [(VALUE_MISMATCH, "REC-1")]


def test_location_mismatch():
    result = compare({"REC-1": a_rec()}, [entry(location="LOC-102")])
    assert reasons(result) == [(LOCATION_MISMATCH, "REC-1")]


def test_date_mismatch():
    result = compare({"REC-1": a_rec()}, [entry(when=date(2026, 3, 3))])
    assert reasons(result) == [(DATE_MISMATCH, "REC-1")]


def test_voided_record_that_b_still_holds_is_flagged():
    result = compare({"REC-1": a_rec(state="VOIDED")}, [entry()])
    assert reasons(result) == [(VOIDED_IN_A, "REC-1")]


# ---- things that look wrong but are fine ----

def test_clean_row_produces_nothing():
    assert compare({"REC-1": a_rec()}, [entry()]) == []


def test_split_that_adds_up_is_not_an_error():
    b = [entry("E1", value="40.00"), entry("E2", value="60.00")]
    assert compare({"REC-1": a_rec()}, b) == []


def test_split_that_does_not_add_up_is_flagged():
    b = [entry("E1", value="40.00"), entry("E2", value="50.00")]
    assert reasons(compare({"REC-1": a_rec()}, b)) == [(DUPLICATE_IN_B, "REC-1")]


def test_voided_record_with_no_b_entry_is_fine():
    assert compare({"REC-1": a_rec(state="VOIDED")}, []) == []


def test_money_is_compared_exactly_not_as_float():
    # 0.1 + 0.2 != 0.3 with floats. With Decimal the split below adds up exactly.
    b = [entry("E1", value="0.10"), entry("E2", value="0.20")]
    assert compare({"REC-1": a_rec(total="0.30")}, b) == []


def test_messy_references_match_their_records():
    assert normalize_ref("rec1034") == "REC-1034"
    assert normalize_ref(" REC - 1070 ") == "REC-1070"
    assert normalize_ref("1112") == "REC-1112"
    a = {"REC-1034": a_rec(), "REC-1070": a_rec(), "REC-1112": a_rec()}
    b = [entry("E1", ref=normalize_ref("rec1034")),
         entry("E2", ref=normalize_ref(" REC - 1070 ")),
         entry("E3", ref=normalize_ref("1112"))]
    assert compare(a, b) == []


def test_indian_style_commas_are_read_before_comparing():
    assert parse_amount("1,25,400.00") == D("125400.00")
    b = [entry(value=str(parse_amount("1,25,400.00")))]
    assert compare({"REC-1": a_rec(total="125400.00")}, b) == []


def test_blank_and_junk_amounts_are_none_never_zero():
    assert parse_amount("") is None
    assert parse_amount("   ") is None
    assert parse_amount("abc") is None
    assert parse_amount(None) is None
    assert parse_amount("NaN") is None


def test_reference_without_digits_is_an_orphan_not_a_crash():
    assert normalize_ref("n/a") is None
    result = compare({"REC-1": a_rec()}, [entry(), entry("E7", ref=None)])
    assert reasons(result) == [(ORPHAN_IN_B, "E7")]