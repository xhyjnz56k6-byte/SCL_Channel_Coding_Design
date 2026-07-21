# Frame Pool Format

Common-03 frame pools store payload bits only.

## Manifest

The manifest schema is `common03.frame_pool_manifest.v2`.

Required identity fields:

- `payloadPolicyVersion = 1`
- `generationAlgorithm = splitmix64_payload_v2`
- `bitStorageFormat = packed_bits`
- `bitOrderWithinByte = lsb_first`
- `integerByteOrder = not_applicable`
- `overallHash`

`createdTime` is intentionally excluded so the same inputs regenerate byte-identical manifests.

## Packed Bits

- payload `bitIndex = 0` is stored in byte 0 bit 0.
- payload `bitIndex = 7` is stored in byte 0 bit 7.
- payload `bitIndex = 8` is stored in byte 1 bit 0.
- Unused high bits in the final byte are fixed to 0.
- Padding bits are not payload bits.

## overallHash

`overallHash` is SHA256 over canonical UTF-8 text containing stable manifest identity fields and each shard's `startFrame`, `frameCount`, `fileName`, `sizeBytes`, and `sha256`.

It excludes time, absolute paths, usernames, temporary directories, Git paths, operating system data, and line-ending-dependent file bytes.
