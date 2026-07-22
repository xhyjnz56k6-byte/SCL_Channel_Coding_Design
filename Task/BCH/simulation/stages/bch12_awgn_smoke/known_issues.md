# BCH-12 known issues

The initial JSONL publisher dropped one completion line per point by treating JSONL as CSV. Repair
commit `205f82c84811472ace5ca5c45f7ff0d124887b2c` corrected the aggregation and a complete 20-record
rerun passed. No unresolved BCH-12 issue remains. Smoke sample size is intentionally too small for
formal performance claims; BCH-13 and BCH-15 provide the required larger experiments.
