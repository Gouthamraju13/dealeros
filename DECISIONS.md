# Decisions

## Decision: compare B's value with A's total_value
-Rejected: compare with base_value
-Why: B equals A's total_value (base plus adjustment) on almost every row. On three rows (REC-1003, 1027, 1088) B equals the base_value, which means B left out the adjustment. Those are real disagreements, and comparing with base_value would hide them.

## Decision: clean references by taking the digits and rebuilding "REC-<digits>"
-Rejected: exact text match, and fuzzy matching
-Why: rec1034, " REC - 1070 " and 1112 clearly mean REC-1034, REC-1070 and REC-1112. Exact matching would call all three orphans. The original text is always kept in record_ref_raw, and a reference with no digits is kept and treated as an orphan.

## Decision: a blank amount is NULL (unknown), never 0
-Rejected: turning blank or unreadable amounts into 0
-Why: 0 is a real amount, so it would make a missing value look real. A blank B value is flagged as VALUE_MISMATCH and shown as an empty cell. The original text is kept in value_raw, and 1,25,400.00 is read as 125400.00 before comparing.

## Decision: two entries that add up to A's total are a split, anything else is a duplicate
-Rejected: flagging every record that has two B entries
-Why: REC-1055 has two parts that add up exactly to A's total, so it is fine. REC-1042 has the same amount twice, so B holds double and it is flagged as DUPLICATE_IN_B. The sums use Decimal so the check is exact.

## Decision: a VOIDED record that B still holds is flagged as VOIDED_IN_A
-Rejected: ignoring voided records, or treating B's entry as expected
-Why: if A says the event was cancelled but B still counts it, the two books disagree. A voided record with no B entry is correct and is not reported as missing. This is the decision I am least sure about.

## Decision: date and location differences count as disagreements
-Rejected: reporting only the four required reasons
-Why: the brief says the four are the minimum. A record at a different location or date in B is something someone would want to know. They are separate reasons (DATE_MISMATCH, LOCATION_MISMATCH) so they can be filtered out.

## Decision: the cross-org row (REC-1077) belongs only to the org that owns A's side, and B's side is hidden
-Rejected: showing "A says LOC-102, B says LOC-201" to ORG-A, and showing the row to both orgs
-Why: showing LOC-201 would reveal an ORG-B location to ORG-A, and showing the row to ORG-B would reveal ORG-A's record. So only ORG-A sees it, and B's location and value are replaced by "hidden (other org)". B's side is never saved on that row at all. The cost is that ORG-B is never told about its stray entry.

## Decision: the org filter happens inside the database query
-Rejected: loading every disagreement and hiding the other org's rows in Python or React
-Why: hidden data is still leaked data, because anyone can open the browser's network tab. Each disagreement is saved with its owning org, worked out only from the Location table and never from the ID pattern. The API always filters by org in the query, and refuses a request with no org or an unknown org. An orphan belongs to the org of B's own location.

## Decision: SQLite and Decimal for money
-Rejected: Postgres, and float for money
-Why: SQLite comes with Django, so a reviewer needs no setup. Decimal compares money exactly, while floats cannot (0.1 + 0.2 is not 0.3).