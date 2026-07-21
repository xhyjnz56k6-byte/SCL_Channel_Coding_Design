# Common-02 Stage Plan

## Stage

```text
stage02_common_types_interfaces
```

Branch:

```text
stage02-03-common-foundation
```

Gate:

```text
PASS_COMMON_TYPES_INTERFACES
```

## 目标

建立 Common-01 定义之上的公共 C++ 类型和接口骨架，供后续帧池、信道、指标和三类编码接入使用。

## 非目标

不实现 BCH、卷积码、LDPC、BPSK、AWGN、sigma、标准高斯噪声、LLR、BER/FER、置信区间、stop controller、checkpoint/resume、交织或仿真 runner。

## 允许修改范围

```text
Task/Common/CMakeLists.txt
Task/Common/include/common/
Task/Common/src/
Task/Common/tests/stage02/
Task/Common/scripts/build_common02.py
Task/Common/scripts/check_common02.py
Task/Common/stages/stage02_common_types_interfaces/
```

## 禁止修改范围

```text
Task/BCH/
Task/CC/
Task/LDPC/
Task/Common/Plan/
Common-03 frame pool implementation
```

## 输入

- Common-01 frozen definitions and schema.
- `AGENTS.md`.
- `初始规划/CODEX_GIT_WORKFLOW.md`.
- Batch A task brief.

## 输出

- Common C++17 headers for fixed-width types, frame records, decoder input variants, result/checkpoint records, and interfaces.
- A small translation unit that verifies header compilation without implementing algorithms.
- Stage02 C++ tests.
- Build and check scripts.
- Stage02 audit files and snapshot.

## 测试计划

```powershell
python Task\Common\scripts\build_common02.py
python Task\Common\scripts\check_common02.py
```

The check script builds and runs the C++ test executable, scans for forbidden dependencies or implementations, validates snapshot SHA256 consistency, checks negative tests, and checks the committed diff boundary.

## 负向测试计划

- `encodedLength = 0`
- payload bit `2`
- `payloadBits.size() != payloadLength`
- DecoderInput type conflict
- ambiguous `SNR` checkpoint field
- missing virtual destructor text scan
- forbidden BCH/CC/LDPC include scan

## 停止边界

Stop after Common-02 Gate. Do not enter Common-03 until the user confirms.

