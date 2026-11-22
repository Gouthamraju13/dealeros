"""Tests that use the database: the importer and tenant isolation, on the real CSV files."""
import io
import json

import pytest
from django.core.management import call_command
from django.test import Client

from reconcile.models import Disagreement, Location, SystemARecord, SystemBEntry

pytestmark = pytest.mark.django_db


@pytest.fixture
def loaded():
    call_command("import_data", stdout=io.StringIO())


def get(org, **params):
    resp = Client().get("/api/disagreements/", {"org": org, **params})
    return resp.status_code, json.loads(resp.content)


# ---- importer ----

def test_every_row_is_saved(loaded):
    assert SystemARecord.objects.count() == 120
    assert SystemBEntry.objects.count() == 121  # the extra row is on purpose
    assert Location.objects.count() == 5


def test_running_the_import_twice_does_not_duplicate_rows(loaded):
    call_command("import_data")
    assert SystemARecord.objects.count() == 120
    assert SystemBEntry.objects.count() == 121
    assert Disagreement.objects.count() == 12


def test_dirty_values_are_kept_as_null_with_original_text(loaded):
    blank = SystemBEntry.objects.get(entry_id="ENT/2026/4050")
    assert blank.value is None and blank.value_raw == ""
    commas = SystemBEntry.objects.get(entry_id="ENT/2026/4064")
    assert str(commas.value) == "125400.00" and commas.value_raw == "1,25,400.00"
    assert SystemARecord.objects.filter(actor_id__isnull=True).count() == 1


def test_messy_refs_are_cleaned_but_original_is_kept(loaded):
    e = SystemBEntry.objects.get(entry_id="ENT/2026/4070")
    assert e.record_ref == "REC-1070" and e.record_ref_raw == "REC - 1070"


def test_real_data_finds_the_expected_disagreements(loaded):
    found = {(d.reason, d.record_id) for d in Disagreement.objects.all()}
    assert found == {
        ("MISSING_IN_B", "REC-1015"), ("MISSING_IN_B", "REC-1061"),
        ("ORPHAN_IN_B", "REC-1999"),
        ("DUPLICATE_IN_B", "REC-1042"),
        ("VALUE_MISMATCH", "REC-1003"), ("VALUE_MISMATCH", "REC-1027"),
        ("VALUE_MISMATCH", "REC-1050"), ("VALUE_MISMATCH", "REC-1064"),
        ("VALUE_MISMATCH", "REC-1088"),
        ("DATE_MISMATCH", "REC-1009"),
        ("LOCATION_MISMATCH", "REC-1077"),
        ("VOIDED_IN_A", "REC-1019"),
    }
    # The split (REC-1055) and the messy references must NOT appear.
    flagged = {rid for _, rid in found}
    assert not flagged & {"REC-1055", "REC-1034", "REC-1070", "REC-1112"}


# ---- tenant isolation ----

def org_of(location_id):
    return Location.objects.get(location_id=location_id).org_id


def test_each_org_sees_only_its_own_locations_and_records(loaded):
    for org in ("ORG-A", "ORG-B"):
        status, rows = get(org)
        assert status == 200 and rows
        for row in rows:
            assert org_of(row["location"]) == org, row


def test_org_a_never_sees_org_b_records(loaded):
    _, rows = get("ORG-A")
    a_ids = set(SystemARecord.objects.filter(location__org_id="ORG-A").values_list("record_id", flat=True))
    b_orphans = set(SystemBEntry.objects.filter(location__org_id="ORG-A").values_list("record_ref", flat=True))
    for row in rows:
        assert row["record_id"] in a_ids | b_orphans
    assert "LOC-201" not in json.dumps(rows) and "LOC-202" not in json.dumps(rows)


def test_org_b_never_sees_org_a_records(loaded):
    _, rows = get("ORG-B")
    text = json.dumps(rows)
    assert "LOC-101" not in text and "LOC-102" not in text and "LOC-103" not in text
    assert "REC-1077" not in text  # the cross-org row belongs only to ORG-A
    assert "REC-1999" not in text  # the orphan sits at an ORG-A location


def test_cross_org_row_hides_the_other_orgs_location_and_value(loaded):
    _, rows = get("ORG-A")
    row = next(r for r in rows if r["record_id"] == "REC-1077")
    assert row["reason"] == "LOCATION_MISMATCH"
    assert row["location"] == "LOC-102"
    assert row["b_hidden"] is True and row["b_value"] is None
    assert "LOC-201" not in json.dumps(row)


def test_filter_and_sort_stay_inside_the_org(loaded):
    for org in ("ORG-A", "ORG-B"):
        _, rows = get(org, reason="VALUE_MISMATCH", sort="-value")
        assert all(r["reason"] == "VALUE_MISMATCH" for r in rows)
        assert all(org_of(r["location"]) == org for r in rows)
        values = [float(r["a_value"]) for r in rows]
        assert values == sorted(values, reverse=True)


def test_sort_puts_rows_with_no_value_last(loaded):
    _, rows = get("ORG-A", sort="b_value")
    seen_none = False
    for r in rows:
        if r["b_value"] is None:
            seen_none = True
        else:
            assert not seen_none, "a row with a value came after an empty one"


def test_api_needs_a_known_org(loaded):
    assert Client().get("/api/disagreements/").status_code == 400
    assert Client().get("/api/disagreements/", {"org": "ORG-Z"}).status_code == 404
    assert Client().get("/api/disagreements/", {"org": "ORG-A", "reason": "NOPE"}).status_code == 400