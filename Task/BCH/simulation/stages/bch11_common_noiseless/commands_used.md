# BCH-11 commands

```text
python Task/Common/scripts/generate_common03_frame_pool.py --output-dir Task/BCH/simulation/build/frame_pool_k200 --payload-length 200 --frame-count 200 --shard-size 100 --master-seed 2026072001 --overwrite
python Task/Common/scripts/generate_common03_frame_pool.py --output-dir Task/BCH/simulation/build/frame_pool_k300 --payload-length 300 --frame-count 200 --shard-size 100 --master-seed 2026072001 --overwrite
cmake -S Task/BCH/simulation/current -B Task/BCH/simulation/build/current -G "MinGW Makefiles" -DCMAKE_BUILD_TYPE=Release -DBCH_K200_MANIFEST=.../k200/manifest.json -DBCH_K300_MANIFEST=.../k300/manifest.json
cmake --build Task/BCH/simulation/build/current --config Release -j 4
ctest --test-dir Task/BCH/simulation/build/current --output-on-failure -R bch11_common_noiseless
Task/BCH/simulation/build/current/test_bch11_noiseless.exe .../k200/manifest.json .../k300/manifest.json Task/BCH/simulation/stages/bch11_common_noiseless
```
