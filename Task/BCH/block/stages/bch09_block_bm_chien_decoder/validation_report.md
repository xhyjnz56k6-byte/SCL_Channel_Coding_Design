# Validation report

Executed `python Task/BCH/block/scripts/run_bch_group3.py --all` with MATLAB 24.2 R2024b/PCWIN64 and Communications Toolbox 24.2. Counts: {"noErrorRows": 416, "singleAllRows": 5104, "weight2ToTRows": 1400, "uncorrectableRows": 1248, "overCapabilityPatternModes": 7}. All applicable field mismatches are zero. BCH-06 regression passed 4/4 CTest plus single-block and segmented MATLAB checkers.

BM final locator is compared exactly; per-iteration discrepancy/degree history is not claimed.

Gate: `PASS_BCH09_BLOCK_ALGEBRAIC_DECODER`.
