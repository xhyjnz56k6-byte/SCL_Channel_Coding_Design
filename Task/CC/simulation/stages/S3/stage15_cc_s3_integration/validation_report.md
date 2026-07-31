# stage15_cc_s3_integration validation report

- Branch: `stage01-cc`
- Functional range: `661480f684e2ba9793f4a804d96bb07b794ea4fa...199a225d342ca3b192d590587eb4d068e73eea63`
- Remote functional commit verified: PASS
- Merge status: NOT_MERGED

## Executed checks

- Formal-source-only matrix: 3447 rows: PASS
- Stage14 matrix contribution: Hard 372 + Soft 372, all four organizations: PASS
- Stage10 real filter values printed and verified; FER_010 finite-depth points: 18: PASS
- Twelve focused plots and figure-data CSVs: non-empty PASS
- Representative latency/reliability points: 9: PASS
- Fair recommendation bases: fixed FER=0.1 or fixed Es/N0=2.0 dB: PASS
- Five recommendation classes, all `coveredByData=true`: PASS
- Chinese Stage14/15 analysis and final report with valid image paths: PASS
- `python scripts/check_stage15_revision.py`: PASS

Final status: **PASS_CC_S3_FINAL_DELIVERY**

## Log-scale redraw

- Zero-error BER/FER points remain in formal CSV and figure-data: PASS
- Log-scale plots omit zero values instead of clipping to 1e-8: PASS
- Rebuilt PNGs, manifests and Stage14/15 checkers: PASS
