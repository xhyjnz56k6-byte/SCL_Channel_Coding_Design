# Common-01 Stage Plan

## Stage

```text
stage01_common_definition
```

Branch:

```text
stage01-common-definition
```

Gate:

```text
PASS_COMMON_DEFINITION
```

## 目标

冻结后续公共仿真必须遵守的数学定义、字段定义、随机性公平规则、停止规则、结果 schema 和审计规则。

## 非目标

本阶段不实现公共帧池、随机 payload 生成器、标准高斯噪声生成器、BPSK/AWGN/硬判决/LLR C++ 类、BER/FER C++ 统计类、checkpoint 读写、simulation runner、Identity Codec、BCH、卷积码、LDPC、smoke/prescan/formal 仿真或性能曲线。

## 允许修改范围

```text
Task/Common/config/
Task/Common/docs/
Task/Common/scripts/
Task/Common/stages/stage01_common_definition/
```

## 禁止修改范围

```text
Task/BCH/
Task/CC/
Task/LDPC/
其他旧 Stage
其他旧结果
其他模块源码
```

## 输入

- `AGENTS.md`
- `初始规划/CODEX_GIT_WORKFLOW.md`
- `初始规划/v2.0-三类信道编码公共基础仿真详细规划.md`
- `初始规划/三类信道编码公共基础仿真规划_码率定义修订版.md`
- Common-01 任务说明

## 输出

- JSON 配置：`global_config.json`、`seed_policy.json`、`stop_rules.json`、`result_schema.json`
- Markdown 定义文档
- Python 定义检查脚本
- Stage 审计文件和 snapshot

## 定义清单

- `K_payload`、`K_codec_input`、`N_encoded`、`N_transmitted`
- `fillerLength`、`crcLength`、`tailLength`、`puncturedLength`、`shortenedLength`
- `R = K_payload/N_encoded`
- BPSK: `0 -> +1`, `1 -> -1`
- AWGN: `y = x + sigma*z`
- `sigma^2 = 1/(2*R*10^(EbN0_dB/10))`
- hard decision: `y >= 0 -> 0`, `y < 0 -> 1`
- LLR: `2*y/sigma^2`, positive means bit 0
- payload-only BER/FER
- payload success and decoder declared success are separate
- undetected error definition
- Wilson 95% confidence interval
- zero-error plot upper-bound policy
- four stop-rule levels and stop logic
- `noiseGroupId` and cross-SNR standard Gaussian reuse
- LDPC interleaver forbidden
- point result and curve summary separation
- checkpoint required fields
- plot naming template and overwrite policy

## 验证计划

1. Run `python Task\Common\scripts\validate_common01_definition.py`.
2. Run `python Task\Common\scripts\validate_common01_definition.py --negative-tests`.
3. Run `git status --short --branch`.
4. Run `git diff --stat`.
5. Run `git diff -- Task/Common`.
6. Confirm no changes under `Task/BCH`, `Task/CC`, or `Task/LDPC`.

## 负向测试计划

The validation script mutates temporary copies and must fail these cases:

- `reuseNoiseAcrossSnr = false`
- delete `K_payload`
- put `decoderType` into `noiseSeedFields`
- set LDPC `interleaverAllowed = true`
- set `maxFrames < minFrames`
- change rate definition to `K_codec_input/N_encoded`
- delete a required checkpoint field

## 停止边界

Stop after Common-01 definitions, validation, negative tests, and audit records. Do not enter Common-02. Do not merge `main`.

