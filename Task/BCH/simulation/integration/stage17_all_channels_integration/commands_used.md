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
git merge --no-ff origin/stage09-12-bch-s2-cfo-blockage -m "BCH/stage17：合并CFO与短时遮挡基础线路"
git config core.longpaths true
git merge --no-ff origin/stage09-12-bch-s2-cfo-blockage -m "BCH/stage17：合并CFO与短时遮挡基础线路"
python Task\BCH\simulation\stages\S2\stage09_cfo_validation\python\stage09_cfo_validation_checker.py
python Task\BCH\simulation\stages\S2\stage10_cfo_formal\python\stage10_cfo_formal_checker.py
python Task\BCH\simulation\stages\S2\stage11_blockage_validation\python\stage11_blockage_validation_checker.py
python Task\BCH\simulation\stages\S2\stage12_blockage_formal\python\stage12_blockage_formal_checker.py
python \\?\C:\Users\V3169\Desktop\Project\SCL_Channel_Coding_Design_stage17_integration\Task\BCH\simulation\stages\S2\stage12_blockage_formal\experiment_c_fixed_length\python\stage12_blockage_formal_experiment_c_fixed_length_checker.py
git merge --no-ff origin/stage10-12-bch-s2-dense-snr-rerun -m "BCH/stage17：合并CFO遮挡高密度线路"
python Task\BCH\simulation\stages\S2\stage10_cfo_formal\python\stage10_cfo_formal_checker.py
python Task\BCH\simulation\stages\S2\stage12_blockage_formal\python\stage12_blockage_formal_checker.py
git merge --no-ff origin/stage13-16-bch-s2-burst-interleaving -m "BCH/stage17：合并突发错误与交织线路"
python Task\BCH\simulation\stages\S2\stage13_burst_interleaving_validation\python\stage13_burst_interleaving_validation_check.py
python Task\BCH\simulation\stages\S2\stage14_burst_formal\python\stage14_burst_formal_check.py
python Task\BCH\simulation\stages\S2\stage15_interleaving_formal\python\stage15_interleaving_formal_check.py
python Task\BCH\simulation\stages\S2\stage16_burst_interleaving_comparison\python\stage16_burst_interleaving_comparison_check.py
git merge-base --is-ancestor origin/stage07-bch-s2-awgn-dense-formal HEAD
git merge-base --is-ancestor origin/stage07-08-bch-s2-multipath HEAD
git merge-base --is-ancestor origin/stage10-12-bch-s2-dense-snr-rerun HEAD
git merge-base --is-ancestor origin/stage13-16-bch-s2-burst-interleaving HEAD
git diff --check origin/main...HEAD
git diff --name-only origin/main...HEAD -- Task/CC Task/LDPC
```
