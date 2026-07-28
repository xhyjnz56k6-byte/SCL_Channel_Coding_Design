# Stage17 BCH S2 Integration Dependency Graph

```mermaid
graph TD
    main["origin/main"]
    stage01_06_bch_s2_awgn["stage01-06-bch-s2-awgn"] --> stage07_bch_s2_awgn_dense_formal["stage07-bch-s2-awgn-dense-formal"]
    stage01_06_bch_s2_awgn["stage01-06-bch-s2-awgn"] --> stage09_12_bch_s2_cfo_blockage["stage09-12-bch-s2-cfo-blockage"]
    stage09_12_bch_s2_cfo_blockage["stage09-12-bch-s2-cfo-blockage"] --> stage10_12_bch_s2_dense_snr_rerun["stage10-12-bch-s2-dense-snr-rerun"]
    stage01_06_bch_s2_awgn["stage01-06-bch-s2-awgn"] --> stage13_16_bch_s2_burst_interleaving["stage13-16-bch-s2-burst-interleaving"]
    main --> stage01_06_bch_s2_awgn["stage01-06-bch-s2-awgn"]
    main --> stage07_08_bch_s2_multipath["stage07-08-bch-s2-multipath"]
```

| A | B | A ancestor of B | B ancestor of A |
|---|---|---|---|
| `stage01-06-bch-s2-awgn` | `stage07-bch-s2-awgn-dense-formal` | TRUE | FALSE |
| `stage01-06-bch-s2-awgn` | `stage09-12-bch-s2-cfo-blockage` | TRUE | FALSE |
| `stage09-12-bch-s2-cfo-blockage` | `stage10-12-bch-s2-dense-snr-rerun` | TRUE | FALSE |
| `stage01-06-bch-s2-awgn` | `stage13-16-bch-s2-burst-interleaving` | TRUE | FALSE |
| `stage01-06-bch-s2-awgn` | `stage07-08-bch-s2-multipath` | FALSE | FALSE |
| `stage07-bch-s2-awgn-dense-formal` | `stage07-08-bch-s2-multipath` | FALSE | FALSE |
| `stage07-bch-s2-awgn-dense-formal` | `stage10-12-bch-s2-dense-snr-rerun` | FALSE | FALSE |
| `stage09-12-bch-s2-cfo-blockage` | `stage13-16-bch-s2-burst-interleaving` | FALSE | FALSE |
