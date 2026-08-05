# Stage10 命令

```text
s7_formal_runner BCH stage10_bch_formal/checkpoint_resume_test --group-limit 2 --interrupt-after-checkpoint
s7_formal_runner BCH stage10_bch_formal/checkpoint_resume_test --group-limit 2
s7_formal_runner BCH stage10_bch_formal/checkpoint_clean_test --group-limit 2
s7_formal_runner BCH stage10_bch_formal/results
python scripts/check_formal.py BCH stage10_bch_formal/results
```
