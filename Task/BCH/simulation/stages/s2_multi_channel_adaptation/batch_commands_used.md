# Commands used

```text
cmake -S Task/BCH/simulation/current -B Task/BCH/simulation/build/current -DCMAKE_BUILD_TYPE=Release
cmake --build Task/BCH/simulation/build/current --config Release -j 4
ctest --test-dir Task/Common/build/stage04 -C Release --output-on-failure
ctest --test-dir Task/BCH/simulation/build/current -C Release --output-on-failure
python Task/BCH/simulation/scripts/run_bch_s2_batch2.py --smoke-only --no-progress --resume
python Task/BCH/simulation/scripts/run_bch_s2_batch2.py --stage s2_05 --formal-only --no-progress --resume
python Task/BCH/simulation/scripts/run_bch_s2_batch2.py --stage s2_06 --formal-only --no-progress --resume
python Task/BCH/simulation/scripts/run_bch_s2_batch2.py --stage s2_07 --formal-only --no-progress --resume
python Task/BCH/simulation/scripts/compare_bch_s2_batch2.py
python Task/BCH/simulation/scripts/plot_bch_s2_batch2.py
python Task/BCH/simulation/scripts/check_bch_s2_batch2_resume_shard.py
matlab -batch "run_bch_s2_batch2_reference(...)"
python Task/BCH/simulation/scripts/check_bch_s2_batch2.py
```
