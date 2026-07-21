#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest")
    args = parser.parse_args()
    data = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    print(json.dumps({
        "noisePoolId": data["noisePoolId"],
        "totalFrames": data["totalFrames"],
        "symbolsPerFrame": data["symbolsPerFrame"],
        "shards": len(data["shards"]),
        "overallHash": data["overallHash"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
