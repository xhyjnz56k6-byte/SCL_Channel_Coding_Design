# BCH-13 commands

```text
python -m py_compile Task/BCH/simulation/scripts/run_bch_group4.py Task/BCH/simulation/scripts/plot_bch_prescan.py
python Task/BCH/simulation/scripts/run_bch_group4.py --dry-run --no-progress
python Task/BCH/simulation/scripts/run_bch_group4.py --stage bch13 --progress --progress-refresh-seconds 0.5
python Task/BCH/simulation/scripts/audit_bch_group4.py --stage bch13 --results-dir Task/BCH/simulation/results/prescan --stage-dir Task/BCH/simulation/stages/bch13_awgn_prescan
```
