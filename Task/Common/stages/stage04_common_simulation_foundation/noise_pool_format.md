# Common-04 Noise Pool Format

Noise shards are binary files with a versioned header followed by float64 little-endian Gaussian samples in frame-major order.

Header fields are serialized one by one:

1. `magic = SCLN04`
2. `headerVersion = 1`
3. `firstFrameIndex`
4. `frameCount`
5. `symbolsPerFrame`
6. `masterNoiseSeed`
7. `noiseGroupId`
8. `noisePolicyVersion`

Raw C++ struct memory serialization is forbidden.

`payloadDataHash` is intentionally omitted. Common-04 noise identity is covered by complete shard SHA256 values plus the manifest `overallHash`; Common-03 remains responsible for frame-pool payload identity.

Large noise pools are generated under `build/` or temporary directories and are not committed.
