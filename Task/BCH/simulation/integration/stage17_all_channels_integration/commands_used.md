# Stage17 Commands Used

```text
git worktree add -b stage17-all-channels-integration C:\Users\V3169\Desktop\Project\SCL_Channel_Coding_Design_stage17_integration origin/main
python Task\BCH\simulation\integration\stage17_all_channels_integration\python\stage17_generate_inventory.py
git merge --no-ff origin/stage07-bch-s2-awgn-dense-formal -m "BCH/stage17：合并AWGN高密度线路"
python Task\BCH\simulation\stages\S2\stage07_awgn_dense_formal\python\stage07_awgn_dense_formal_check.py
python Task\BCH\simulation\stages\S2\stage07_awgn_dense_formal\python\stage07_awgn_dense_formal_audit.py
git ls-tree -r --name-only origin/stage07-bch-s2-awgn-dense-formal Task/BCH/simulation/stages/S2/stage07_awgn_dense_formal/results/points
python Task\BCH\simulation\integration\stage17_all_channels_integration\stage17_awgn_dense_source_attestation.py
python Task\BCH\simulation\integration\stage17_all_channels_integration\stage17_awgn_dense_integration_check.py
git merge --no-ff origin/stage07-08-bch-s2-multipath -m "BCH/stage17：合并多径common-SNR线路"
python Task\BCH\simulation\stages\S2\stage08_multipath_formal_common_snr\python\stage08_multipath_formal_common_snr_check.py
python Task\BCH\simulation\stages\S2\stage08_multipath_formal_common_snr\python\stage08_multipath_formal_common_snr_plot_check.py
python Task\BCH\simulation\stages\S2\stage08_multipath_formal_common_snr\python\stage08_multipath_formal_common_snr_finalize_audit.py
git restore -- Task/BCH/simulation/stages/S2/stage08_multipath_formal_common_snr/stage08_multipath_formal_common_snr_file_hashes.json Task/BCH/simulation/stages/S2/stage08_multipath_formal_common_snr/stage08_multipath_formal_common_snr_manifest.json Task/BCH/simulation/stages/S2/stage08_multipath_formal_common_snr/stage08_multipath_formal_common_snr_validation_report.md
```
