#!/usr/bin/env python
"""Validate Common-02 public types and interfaces."""

from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


REQUIRED_FILES = [
    "Task/Common/CMakeLists.txt",
    "Task/Common/include/common/types.hpp",
    "Task/Common/include/common/frame.hpp",
    "Task/Common/include/common/decoder_input.hpp",
    "Task/Common/include/common/result_types.hpp",
    "Task/Common/include/common/interfaces.hpp",
    "Task/Common/include/common/common.hpp",
    "Task/Common/src/common_interfaces.cpp",
    "Task/Common/tests/stage02/test_common02_types_interfaces.cpp",
    "Task/Common/scripts/build_common02.py",
    "Task/Common/scripts/check_common02.py",
    "Task/Common/stages/stage02_common_types_interfaces/stage_plan.md",
    "Task/Common/stages/stage02_common_types_interfaces/changed_files.md",
    "Task/Common/stages/stage02_common_types_interfaces/validation_report.md",
    "Task/Common/stages/stage02_common_types_interfaces/manifest.json",
    "Task/Common/stages/stage02_common_types_interfaces/changes.patch",
    "Task/Common/stages/stage02_common_types_interfaces/frozen_config.csv",
    "Task/Common/stages/stage02_common_types_interfaces/commands_used.md",
    "Task/Common/stages/stage02_common_types_interfaces/git_commit.txt",
    "Task/Common/stages/stage02_common_types_interfaces/known_issues.md",
    "Task/Common/stages/stage02_common_types_interfaces/snapshot/README.md",
]

SNAPSHOT_PAIRS = [
    ("Task/Common/CMakeLists.txt", "Task/Common/stages/stage02_common_types_interfaces/snapshot/CMakeLists.txt"),
    ("Task/Common/include/common/types.hpp", "Task/Common/stages/stage02_common_types_interfaces/snapshot/include/common/types.hpp"),
    ("Task/Common/include/common/frame.hpp", "Task/Common/stages/stage02_common_types_interfaces/snapshot/include/common/frame.hpp"),
    ("Task/Common/include/common/decoder_input.hpp", "Task/Common/stages/stage02_common_types_interfaces/snapshot/include/common/decoder_input.hpp"),
    ("Task/Common/include/common/result_types.hpp", "Task/Common/stages/stage02_common_types_interfaces/snapshot/include/common/result_types.hpp"),
    ("Task/Common/include/common/interfaces.hpp", "Task/Common/stages/stage02_common_types_interfaces/snapshot/include/common/interfaces.hpp"),
    ("Task/Common/include/common/common.hpp", "Task/Common/stages/stage02_common_types_interfaces/snapshot/include/common/common.hpp"),
    ("Task/Common/src/common_interfaces.cpp", "Task/Common/stages/stage02_common_types_interfaces/snapshot/src/common_interfaces.cpp"),
    ("Task/Common/tests/stage02/test_common02_types_interfaces.cpp", "Task/Common/stages/stage02_common_types_interfaces/snapshot/tests/stage02/test_common02_types_interfaces.cpp"),
    ("Task/Common/scripts/build_common02.py", "Task/Common/stages/stage02_common_types_interfaces/snapshot/scripts/build_common02.py"),
    ("Task/Common/scripts/check_common02.py", "Task/Common/stages/stage02_common_types_interfaces/snapshot/scripts/check_common02.py"),
]

ALLOWED_PREFIXES = [
    "Task/Common/CMakeLists.txt",
    "Task/Common/include/common/",
    "Task/Common/src/",
    "Task/Common/tests/stage02/",
    "Task/Common/scripts/build_common02.py",
    "Task/Common/scripts/check_common02.py",
    "Task/Common/stages/stage02_common_types_interfaces/",
]

FORBIDDEN_INCLUDE_MARKERS = [
    "Task/BCH",
    "Task/CC",
    "Task/LDPC",
    "../BCH",
    "../CC",
    "../LDPC",
]

FORBIDDEN_IMPLEMENTATION_MARKERS = [
    "normal_distribution",
    "AWGN",
    "Awgn",
    "BPSK",
    "LLR_i =",
    "Wilson",
    "BER =",
    "FER =",
    "Viterbi",
    "Layered BP",
    "Layered NMS",
]


def run(command: list[str], root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=str(root), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def add_failure(failures: list[str], message: str) -> None:
    failures.append(message)


def check_required_files(root: Path, failures: list[str]) -> None:
    for relative in REQUIRED_FILES:
        if not (root / relative).is_file():
            add_failure(failures, f"missing required file: {relative}")


def check_snapshot(root: Path, failures: list[str]) -> None:
    for source, snapshot in SNAPSHOT_PAIRS:
        source_path = root / source
        snapshot_path = root / snapshot
        if not snapshot_path.is_file():
            add_failure(failures, f"missing snapshot file: {snapshot}")
            continue
        if source_path.is_file() and sha256_file(source_path) != sha256_file(snapshot_path):
            add_failure(failures, f"snapshot mismatch: {snapshot}")


def check_text_markers(root: Path, failures: list[str]) -> None:
    include_root = root / "Task/Common/include/common"
    test_root = root / "Task/Common/tests/stage02"
    files = list(include_root.glob("*.hpp")) + list(test_root.glob("*.cpp"))
    joined = "\n".join(path.read_text(encoding="utf-8", errors="ignore") for path in files if path.is_file())
    for marker in FORBIDDEN_INCLUDE_MARKERS:
        if marker in joined:
            add_failure(failures, f"forbidden dependency marker found: {marker}")

    interface_text = (root / "Task/Common/include/common/interfaces.hpp").read_text(encoding="utf-8")
    for expected in [
        "virtual ~IChannelEncoder() = default;",
        "virtual ~IChannelDecoder() = default;",
        "virtual ~IChannel() = default;",
        "virtual ~IFramePoolReader() = default;",
    ]:
        if expected not in interface_text:
            add_failure(failures, f"missing virtual destructor text: {expected}")

    result_text = (root / "Task/Common/include/common/result_types.hpp").read_text(encoding="utf-8")
    if "SnrIndex snrIndex" not in result_text:
        add_failure(failures, "CheckpointRecord must contain snrIndex")
    if "double ebN0_dB" not in result_text:
        add_failure(failures, "CheckpointRecord must contain ebN0_dB")
    if " SNR" in result_text or "\nSNR" in result_text:
        add_failure(failures, "ambiguous SNR field name found")

    types_text = (root / "Task/Common/include/common/types.hpp").read_text(encoding="utf-8")
    if "using Bit = std::uint8_t;" not in types_text:
        add_failure(failures, "Bit must be std::uint8_t")
    if "std::vector<bool>" in types_text:
        add_failure(failures, "std::vector<bool> must not be used")

    implementation_scan = "\n".join(path.read_text(encoding="utf-8", errors="ignore") for path in include_root.glob("*.hpp"))
    for marker in FORBIDDEN_IMPLEMENTATION_MARKERS:
        if marker in implementation_scan:
            add_failure(failures, f"forbidden implementation marker found in headers: {marker}")


def check_build_and_test(root: Path, failures: list[str]) -> None:
    build = run([sys.executable, "Task/Common/scripts/build_common02.py"], root)
    if build.returncode != 0:
        add_failure(failures, "build_common02.py failed:\n" + build.stdout + build.stderr)
        return
    test_exe = root / "Task/Common/build/stage02/test_common02_types_interfaces.exe"
    test = run([str(test_exe)], root)
    if test.returncode != 0:
        add_failure(failures, "Common-02 C++ tests failed:\n" + test.stdout + test.stderr)


def compile_snippet(root: Path, code: str) -> subprocess.CompletedProcess[str]:
    with tempfile.TemporaryDirectory(prefix="common02_neg_") as temp:
        source = Path(temp) / "negative.cpp"
        output = Path(temp) / "negative.exe"
        source.write_text(code, encoding="utf-8")
        command = [
            "g++",
            "-std=c++17",
            "-I",
            str(root / "Task/Common/include"),
            str(source),
            "-o",
            str(output),
        ]
        return run(command, root)


def check_negative_tests(root: Path, failures: list[str]) -> None:
    runtime_tests = [
        (
            "encodedLength = 0",
            r'''
#include "common/types.hpp"
int main() {
    scl::common::CodeLengths lengths{200, 200, 0, 248, 0, 0, 0, 0, 0};
    try { scl::common::validateCodeLengths(lengths); } catch (const std::invalid_argument& ex) {
        return std::string(ex.what()).find("encodedLength") == std::string::npos;
    }
    return 1;
}
''',
        ),
        (
            "payload bit = 2",
            r'''
#include "common/frame.hpp"
int main() {
    scl::common::PayloadFrame frame{"pool", 0, 1, 1, scl::common::BitVector{2}};
    try { scl::common::validatePayloadFrame(frame); } catch (const std::invalid_argument& ex) {
        return std::string(ex.what()).find("non-binary") == std::string::npos;
    }
    return 1;
}
''',
        ),
        (
            "payloadBits.size != payloadLength",
            r'''
#include "common/frame.hpp"
int main() {
    scl::common::PayloadFrame frame{"pool", 0, 2, 1, scl::common::BitVector{0}};
    try { scl::common::validatePayloadFrame(frame); } catch (const std::invalid_argument& ex) {
        return std::string(ex.what()).find("payloadLength") == std::string::npos;
    }
    return 1;
}
''',
        ),
    ]
    for name, code in runtime_tests:
        result = compile_snippet(root, code)
        if result.returncode != 0:
            add_failure(failures, f"negative runtime test failed to confirm expected reason: {name}\n{result.stdout}{result.stderr}")

    compile_fail_tests = [
        (
            "DecoderInput type conflict",
            r'''
#include "common/decoder_input.hpp"
int main() {
    scl::common::DecoderInput input = scl::common::HardBitInput{{0, 1}};
    auto bad = input.hardBits;
    (void)bad;
    return 0;
}
''',
            "hardBits",
        ),
        (
            "checkpoint missing ebN0_dB member access fails",
            r'''
#include "common/result_types.hpp"
int main() {
    scl::common::CheckpointRecord checkpoint;
    checkpoint.SNR = 1.0;
    return 0;
}
''',
            "SNR",
        ),
    ]
    for name, code, expected in compile_fail_tests:
        result = compile_snippet(root, code)
        if result.returncode == 0:
            add_failure(failures, f"negative compile test unexpectedly passed: {name}")
        elif expected not in (result.stdout + result.stderr):
            add_failure(failures, f"negative compile test failed for unexpected reason: {name}")

    check_source = (root / "Task/Common/tests/stage02/test_common02_types_interfaces.cpp").read_text(encoding="utf-8")
    if "codecInputLength" not in check_source or "200.0 / 285.0" not in check_source:
        add_failure(failures, "rate misuse negative coverage is missing expected payload/encoded examples")


def check_git_diff(root: Path, failures: list[str]) -> None:
    diff = run(["git", "diff", "--name-only", "main...HEAD"], root)
    if diff.returncode != 0:
        add_failure(failures, "git diff main...HEAD failed:\n" + diff.stderr)
        return
    paths = [line.strip().replace("\\", "/") for line in diff.stdout.splitlines() if line.strip()]
    for path in paths:
        if path.startswith("Task/Common/Plan/"):
            add_failure(failures, "Task/Common/Plan must not be committed")
        if path.startswith(("Task/BCH/", "Task/CC/", "Task/LDPC/")):
            add_failure(failures, f"out-of-scope path in committed diff: {path}")
        if not any(path == prefix or path.startswith(prefix) for prefix in ALLOWED_PREFIXES):
            if not path.startswith("Task/Common/stages/stage01_common_definition/"):
                add_failure(failures, f"path not allowed for Common-02: {path}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".", help="Repository root")
    args = parser.parse_args()
    root = Path(args.root).resolve()

    failures: list[str] = []
    check_required_files(root, failures)
    if not failures:
        check_snapshot(root, failures)
        check_text_markers(root, failures)
        check_build_and_test(root, failures)
        check_negative_tests(root, failures)
        check_git_diff(root, failures)

    if failures:
        print("COMMON-02 CHECK: FAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("COMMON-02 CHECK: PASS")
    print("Gate: PASS_COMMON_TYPES_INTERFACES")
    return 0


if __name__ == "__main__":
    sys.exit(main())
