# stage14_block_continuous_comparison validation report

- Branch: `stage01-cc`
- Functional range: `661480f684e2ba9793f4a804d96bb07b794ea4fa...199a225d342ca3b192d590587eb4d068e73eea63`
- Remote functional commit verified: PASS
- Merge status: NOT_MERGED

## Executed checks

- Release MinGW build with warnings as errors: PASS
- Hard smoke (10 frames): PASS
- Hard formal grid: 372 rows, 93/93 main units and 93/93 offset units: PASS
- Soft formal reuse: 372 archived rows, no rerun: PASS
- Unified Hard/Soft table: 744 rows: PASS
- Three rates, four organizations, 31 SNR points per case: PASS
- BER/FER/goodput arithmetic and stopping rules: PASS
- Slot/window/output-batch evidence: PASS
- Core PNG and figure-data coverage: 26/26 non-empty: PASS
- `python scripts/check_stage14.py`: PASS

Final status: **PASS_STAGE14_FINAL_DELIVERY**

## Log-scale redraw

- Zero-error BER/FER points remain in formal CSV and figure-data: PASS
- Log-scale plots omit zero values instead of clipping to 1e-8: PASS
- Rebuilt PNGs, manifests and Stage14/15 checkers: PASS
