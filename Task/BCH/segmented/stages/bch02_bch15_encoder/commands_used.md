# Commands used

- Independent Python GF(2) long-division derivation of six authorized fixture vectors.
- `cmake -G "MinGW Makefiles" -S Task/BCH/segmented/current -B Task/BCH/segmented/build/bch02_encoder`
- `cmake --build Task/BCH/segmented/build/bch02_encoder`
- `test_bch15_encoder.exe Task/BCH/segmented/stages/bch02_bch15_encoder`
- `ctest --test-dir Task/BCH/segmented/build/bch02_encoder --output-on-failure`
- Python CSV audit of 2048 generated codewords.
