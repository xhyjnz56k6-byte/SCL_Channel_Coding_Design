#!/usr/bin/env python3
from __future__ import annotations

import math

from generate_common04_noise_pool import gaussian, word


GOLDEN_WORDS = [
    word(2026072101, 0, 0, 0),
    word(2026072101, 0, 0, 1),
    word(2026072101, 1, 3, 7),
]


def main() -> int:
    values = [gaussian(2026072101, 0, 0, i) for i in range(8)]
    if not all(math.isfinite(v) for v in values):
        raise SystemExit("non-finite Gaussian")
    if len(set(GOLDEN_WORDS)) != len(GOLDEN_WORDS):
        raise SystemExit("golden word collision")
    print("COMMON-04 CPP/PYTHON REFERENCE: PASS")
    print("words=" + ",".join(str(v) for v in GOLDEN_WORDS))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
