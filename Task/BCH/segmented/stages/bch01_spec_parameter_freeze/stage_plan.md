# BCH-01: specification, cases, Common contract, and mathematical conventions

## Goal

Freeze the four BCH cases, BCH(15,11,1) segmented conventions, whole-block policy, and the repository-verified integration contract with Common.

## Non-goals

No BCH encoder, syndrome table, decoder, GF(2^m), Berlekamp-Massey, Chien search, AWGN runner, or MATLAB reference implementation is created. No Common behavior changes.

## Scope

Allowed: `Task/BCH/AGENTS.md`, `Task/BCH/README.md`, directory skeleton files, and this Stage directory. Forbidden: all `Task/Common`, `Task/CC`, `Task/LDPC`, and BCH algorithm source files.

## Frozen inputs and outputs

Input is `scl::common::PayloadFrame.payloadBits` with 200 or 300 bits. The future segmented adapter will produce `scl::common::BitVector` of 285 or 420 coded bits. A future hard decoder will accept `scl::common::HardBitInput` and return `scl::common::DecodeResult`.

## Gate

`PASS_BCH01_SPEC_PARAMETER_FREEZE` requires the acceptance matrix, CSV/JSON syntax checks, Common regression, CMake configuration, no forbidden-path changes, and no BCH algorithm implementation. This specification is frozen pending user confirmation; no BCH-02 work may begin in this Stage.

