# BCH Group 4 changed files

Group 4 adds the unified four-case BCH simulation adapter, Common-based AWGN runner, metrics and
progress support, formal checkpoint/resume/shard infrastructure, smoke/prescan/formal/comparison
drivers, matplotlib plotters, strict artifact publishers, Stage records, and curated result evidence.
Common changes are limited to four checkpoint/CMake/test files required for general atomic
checkpoint compatibility. No CC or LDPC file was changed. The full machine-readable file boundary
is the union of functional ranges in the six Stage manifests; `group4_changes.patch` is the branch
overview from the frozen main base through the audited BCH-16 state.
