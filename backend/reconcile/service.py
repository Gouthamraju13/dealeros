"""Glue between the database and the pure compare() function."""
from django.db import transaction

from .compare import compare, ORPHAN_IN_B
from .models import Disagreement, Location, SystemARecord, SystemBEntry


def run_comparison():
    """Compare A and B, then rebuild the Disagreement table. Returns how many rows were saved."""
    # The org of a location comes ONLY from the Location table (locations.csv).
    org_of = dict(Location.objects.values_list("location_id", "org_id"))

    a_rows = {
        a.record_id: {
            "total": a.total_value,
            "location": a.location_raw,
            "date": a.event_date,
            "state": a.state,
        }
        for a in SystemARecord.objects.all()
    }
    b_rows = [
        {
            "entry_id": b.entry_id,
            "ref": b.record_ref,
            "value": b.value,
            "location": b.location_raw,
            "date": b.recorded_on,
        }
        for b in SystemBEntry.objects.all()
    ]

    to_save = []
    for d in compare(a_rows, b_rows):
        # Who owns this row? The org of A's location. An orphan has no A side,
        # so it belongs to the org of B's own location.
        owner_location = d["b_location"] if d["reason"] == ORPHAN_IN_B else d["a_location"]
        org = org_of.get(owner_location)
        if org is None:
            # Unknown location: we cannot say which org owns it, so nobody may see it.
            continue

        b_location, b_value = d["b_location"], d["b_value"]
        cross_org = bool(b_location) and org_of.get(b_location) != org
        if cross_org:
            # B's side lives in ANOTHER org. Never store its location or value on this
            # org's row, so it cannot leak even by accident.
            b_location, b_value = "", None

        difference = None
        if b_value is not None and d["a_value"] is not None:
            difference = b_value - d["a_value"]

        to_save.append(Disagreement(
            org_id=org,
            reason=d["reason"],
            record_id=d["record_id"],
            a_location=d["a_location"],
            b_location=b_location,
            a_value=d["a_value"],
            b_value=b_value,
            difference=difference,
            a_date=d["a_date"],
            b_date=None if cross_org else d["b_date"],
            entry_ids="" if cross_org else ", ".join(d["entry_ids"]),
            cross_org=cross_org,
        ))

    with transaction.atomic():
        Disagreement.objects.all().delete()
        Disagreement.objects.bulk_create(to_save)
    return len(to_save)