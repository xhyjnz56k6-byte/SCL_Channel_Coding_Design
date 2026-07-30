"""Generate the self-contained BG2 table translation unit from the read-only legacy source."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    text = args.source.read_text(encoding="utf-8-sig")
    start = text.index("extern const uint16_t liftSizeTable")
    selected = text[start:]
    selected = selected.replace("extern const uint16_t shiftTableBgn_1", "extern const std::uint16_t ignoredShiftTableBgn_1")
    selected = selected.replace("extern const uint16_t liftSizeTable", "extern const std::uint16_t liftSizeTable")
    selected = selected.replace("extern const uint16_t shiftTableBgn_2", "extern const std::uint16_t shiftTableBgn_2")
    output = (
        '#include "nr_tables.hpp"\n\n'
        "// Mechanically generated from the read-only legacy nrLDPCTables.cpp.\n"
        f"// source_sha256={hashlib.sha256(args.source.read_bytes()).hexdigest()}\n\n"
        + selected
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(output, encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
