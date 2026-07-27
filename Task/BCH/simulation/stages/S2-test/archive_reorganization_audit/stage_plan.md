# S2-test archive reorganization audit plan

Scope is limited to relocating existing BCH S2 code, scripts, tracked Stage
records, MATLAB entry points, and local result archives. No experiment data,
algorithm, random policy, decoder logic, or scientific conclusion may change.

The audit compares source/destination inventories, verifies tracked-file
renames, checks old-path references, rebuilds the relocated C++ targets, and
runs the relocated test entry points.
