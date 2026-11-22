from django.db import models


class Location(models.Model):
    """A branch. Each location belongs to exactly one org (tenant).

    locations.csv is the ONLY place that says which org owns a location.
    """

    location_id = models.CharField(max_length=20, unique=True)
    org_id = models.CharField(max_length=20, db_index=True)
    name = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"{self.location_id} ({self.org_id})"


class SystemARecord(models.Model):
    """One row of system_a.csv: one event as System A recorded it."""

    record_id = models.CharField(max_length=30, unique=True)
    # Nullable so a row pointing at an unknown location is kept, not rejected.
    location = models.ForeignKey(Location, null=True, blank=True, on_delete=models.SET_NULL)
    location_raw = models.CharField(max_length=30, blank=True)
    event_date = models.DateField(null=True, blank=True)
    event_date_raw = models.CharField(max_length=30, blank=True)
    category_code = models.CharField(max_length=20, blank=True)
    actor_id = models.CharField(max_length=30, null=True, blank=True)  # empty in the CSV -> NULL
    base_value = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    adjustment = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    total_value = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    state = models.CharField(max_length=20, blank=True)  # CONFIRMED or VOIDED

    def __str__(self):
        return self.record_id


class SystemBEntry(models.Model):
    """One row of system_b.csv.

    There is deliberately NO foreign key to SystemARecord and record_ref is NOT unique:
    an orphan entry points at a record that does not exist, and a record can have
    several entries (a duplicate, or one amount split into parts).
    """

    entry_id = models.CharField(max_length=40, unique=True)
    record_ref_raw = models.CharField(max_length=60, blank=True)  # exactly what the CSV said
    record_ref = models.CharField(max_length=30, null=True, blank=True, db_index=True)  # cleaned
    location = models.ForeignKey(Location, null=True, blank=True, on_delete=models.SET_NULL)
    location_raw = models.CharField(max_length=30, blank=True)
    recorded_on = models.DateField(null=True, blank=True)
    recorded_on_raw = models.CharField(max_length=30, blank=True)
    value_raw = models.CharField(max_length=40, blank=True)  # exactly what the CSV said
    value = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)  # NULL = unknown
    label = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.entry_id


class Disagreement(models.Model):
    """One row where A and B do not agree. Rebuilt from scratch on every comparison run.

    It is stored in the database (with org_id) so the API can filter by org
    INSIDE the SQL query. Nothing is fetched and then hidden afterwards.
    """

    org_id = models.CharField(max_length=20, db_index=True)
    reason = models.CharField(max_length=30, db_index=True)
    record_id = models.CharField(max_length=40)
    a_location = models.CharField(max_length=30, blank=True)
    b_location = models.CharField(max_length=30, blank=True)
    a_value = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    b_value = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    difference = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)  # b - a
    a_date = models.DateField(null=True, blank=True)
    b_date = models.DateField(null=True, blank=True)
    entry_ids = models.CharField(max_length=200, blank=True)
    # True when B's side of this row belongs to a different org than the viewer's.
    # In that case b_location and b_value were never stored (see service.py).
    cross_org = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.org_id} {self.reason} {self.record_id}"