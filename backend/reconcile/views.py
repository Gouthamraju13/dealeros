from django.db.models import F
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .compare import ALL_REASONS
from .models import Disagreement, Location

# What the "sort" parameter may say. A leading "-" means biggest first.
SORT_FIELDS = {
    "value": "a_value",        # "value" is shorthand for System A's value
    "a_value": "a_value",
    "b_value": "b_value",
    "difference": "difference",
}


def serialize(d):
    """Turn one Disagreement into the JSON the screen needs."""
    return {
        "reason": d.reason,
        "record_id": d.record_id,
        # An orphan has no A side, so its location is B's.
        "location": d.a_location or d.b_location,
        "a_value": None if d.a_value is None else str(d.a_value),
        "b_value": None if d.b_value is None else str(d.b_value),
        "difference": None if d.difference is None else str(d.difference),
        # True means: B's side belongs to another org, so we hide it from this org.
        "b_hidden": d.cross_org,
    }


@api_view(["GET"])
def disagreements(request):
    org = request.query_params.get("org", "").strip()
    if not org:
        return Response({"error": "Please say which org, for example ?org=ORG-A"}, status=400)
    if not Location.objects.filter(org_id=org).exists():
        return Response({"error": f"Unknown org {org!r}"}, status=404)

    # The org filter is part of the database query itself. Rows from other orgs
    # are never loaded, so they cannot leak.
    qs = Disagreement.objects.filter(org_id=org)

    reason = request.query_params.get("reason", "").strip()
    if reason:
        if reason not in ALL_REASONS:
            return Response({"error": f"Unknown reason {reason!r}"}, status=400)
        qs = qs.filter(reason=reason)

    sort = request.query_params.get("sort", "").strip()
    if sort:
        name = sort.lstrip("-")
        if name not in SORT_FIELDS:
            return Response({"error": f"Cannot sort by {name!r}"}, status=400)
        column = F(SORT_FIELDS[name])
        # Rows with no value always go to the bottom, whichever way we sort.
        qs = qs.order_by(column.desc(nulls_last=True) if sort.startswith("-") else column.asc(nulls_last=True), "record_id")
    else:
        qs = qs.order_by("reason", "record_id")

    return Response([serialize(d) for d in qs])


@api_view(["GET"])
def orgs(request):
    """The list of orgs for the dropdown (from locations.csv)."""
    return Response(sorted(Location.objects.values_list("org_id", flat=True).distinct()))


@api_view(["GET"])
def reasons(request):
    return Response(ALL_REASONS)