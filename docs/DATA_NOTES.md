# Notes on the data problems

I opened the three CSV files and looked for odd rows.

- System A has 120 records. System B has 121 entries. The extra one is on purpose.
- Some references in B are written in odd ways: rec1034, " REC - 1070 " and 1112. They all mean real records, so I will clean them into the form REC-1034.
- One value in B is blank. A blank means "unknown", not zero.
- One value in B is 1,25,400.00 (Indian-style commas). I will read it as 125400.00.
- One row in A has an empty actor_id. I will keep the row and store it as empty.
- REC-1999 is in B but not in A. That is an orphan.
- REC-1015 and REC-1061 are in A but have no entry in B.
- REC-1042 appears twice in B with the same amount. That is a real duplicate.
- REC-1055 appears twice in B, and the two amounts add up to A's total. That is a split, not an error.
- REC-1019 is VOIDED in A, but B still has it.
- REC-1003, REC-1027 and REC-1088 have a B value equal to A's base_value instead of total_value.
- REC-1009 has a different date in A and B. REC-1077 has a different location in A and B, and the two locations belong to different orgs.