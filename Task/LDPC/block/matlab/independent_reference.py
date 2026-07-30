"""Independent Python GF(2) matrix/encoder reference for the frozen Direct cases."""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path


def parse_array(text: str, name: str, count: int, width: int) -> list[list[int]]:
    marker = re.search(rf"{re.escape(name)}\s*\[[^\]]+\]\s*\[[^\]]+\]\s*=", text)
    if not marker:
        raise RuntimeError(f"array not found: {name}")
    numbers = [int(value) for value in re.findall(r"\d+", text[marker.end() :])]
    needed = count * width
    if len(numbers) < needed:
        raise RuntimeError(f"short array: {name}")
    return [numbers[index : index + width] for index in range(0, needed, width)]


def rank_and_solve(matrix: list[int], rhs: list[int], columns: int) -> tuple[int, list[int]]:
    rows = len(matrix)
    augmented = [matrix[row] | ((rhs[row] & 1) << columns) for row in range(rows)]
    pivots: list[int] = []
    rank = 0
    for column in range(columns):
        pivot = next((row for row in range(rank, rows) if (augmented[row] >> column) & 1), None)
        if pivot is None:
            continue
        augmented[rank], augmented[pivot] = augmented[pivot], augmented[rank]
        for row in range(rows):
            if row != rank and ((augmented[row] >> column) & 1):
                augmented[row] ^= augmented[rank]
        pivots.append(column)
        rank += 1
        if rank == rows:
            break
    solution = [0] * columns
    for row, column in enumerate(pivots):
        solution[column] = (augmented[row] >> columns) & 1
    return rank, solution


def build_edges(table: list[list[int]], zc: int, set_index: int, nb: int, mb: int) -> list[tuple[int, int]]:
    edges: list[tuple[int, int]] = []
    for row in table:
        base_row, base_column = row[:2]
        if base_row >= mb or base_column >= nb:
            continue
        shift = row[set_index + 2] % zc
        edges.extend(
            (base_row * zc + z, base_column * zc + ((z + shift) % zc))
            for z in range(zc)
        )
    return sorted(edges)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tables", required=True, type=Path)
    parser.add_argument("--cases", required=True, type=Path)
    parser.add_argument("--fixtures", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    text = args.tables.read_text(encoding="utf-8")
    lifts = parse_array(text, "liftSizeTable", 8, 8)
    bg2 = parse_array(text, "shiftTableBgn_2", 197, 10)
    cases = {row["candidateId"]: row for row in csv.DictReader(args.cases.open(encoding="utf-8"))}
    results: list[dict[str, object]] = []
    for fixture in csv.DictReader(args.fixtures.open(encoding="utf-8")):
        case = cases[fixture["caseId"]]
        zc = int(case["Zc"])
        set_index = next(row for row in range(8) if zc in lifts[row])
        nb, mb = int(case["nb"]), int(case["mb"])
        capacity = int(case["informationCapacity"])
        parity = int(case["parityLength"])
        payload = [int(bit) for bit in fixture["payloadBits"]]
        edges = build_edges(bg2, zc, set_index, nb, mb)
        rhs = [0] * parity
        hp = [0] * parity
        for row, column in edges:
            if column < capacity and column < len(payload) and payload[column]:
                rhs[row] ^= 1
            elif column >= capacity:
                hp[row] ^= 1 << (column - capacity)
        rank, parity_bits = rank_and_solve(hp, rhs, parity)
        codeword = payload + [0] * (capacity - len(payload)) + parity_bits
        syndrome = sum(
            sum(codeword[column] for edge_row, column in edges if edge_row == row) & 1
            for row in range(parity)
        )
        expected = "".join(str(bit) for bit in codeword)
        match = expected == fixture["codewordBits"]
        results.append(
            {
                "caseId": fixture["caseId"],
                "pythonRankHp": rank,
                "pythonSyndromeWeight": syndrome,
                "codewordMatch": str(match).lower(),
                "edgeCountMatch": str(len(edges) == int(fixture["edgeCount"])).lower(),
                "status": "PASS" if match and syndrome == 0 and rank == parity else "FAIL",
            }
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(results)
    if any(row["status"] != "PASS" for row in results):
        raise RuntimeError("independent reference mismatch")
    print("PASS_PYTHON_INDEPENDENT_DIRECT_REFERENCE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
