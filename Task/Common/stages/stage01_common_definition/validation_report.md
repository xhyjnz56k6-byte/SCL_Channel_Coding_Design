# Validation Report

## 验证环境

- OS: Windows PowerShell environment
- Repository: `C:\Users\V3169\Desktop\Project\SCL_Channel_Coding_Design`
- Branch: `stage01-common-definition`
- Stage: `stage01_common_definition`

## 执行命令

Results are finalized after the commands are run:

```powershell
python Task\Common\scripts\validate_common01_definition.py
python Task\Common\scripts\validate_common01_definition.py --negative-tests
git status --short --branch
git diff --stat
git diff -- Task/Common
```

## 正常测试

Command:

```powershell
python Task\Common\scripts\validate_common01_definition.py
```

Result:

```text
COMMON-01 VALIDATION: PASS
Gate: PASS_COMMON_DEFINITION
```

## 负向测试

Command:

```powershell
python Task\Common\scripts\validate_common01_definition.py --negative-tests
```

Result: PASS. The script rejected all planned bad mutations:

1. `reuseNoiseAcrossSnr` changed to false.
2. `K_payload` definition deleted.
3. `decoderType` inserted into `noiseSeedFields`.
4. LDPC `interleaverAllowed` changed to true.
5. `maxFrames < minFrames`.
6. Rate definition changed to `K_codec_input/N_encoded`.
7. Required checkpoint field deleted.

## JSON 解析结果

PASS. All four config JSON files and the Stage `manifest.json` parsed successfully with duplicate-key checking enabled.

## 码率样例结果

The script automatically computes:

| case | expected |
|---|---:|
| BCH segmented 200 | 0.7017543859649122 |
| BCH block 200 | 0.8064516129032258 |
| CC 300 1/2 zero tail | 0.49019607843137253 |
| LDPC 300 to 480 | 0.625 |
| LDPC 300 to 576 | 0.5208333333333334 |

## 规则一致性结果

PASS. The script verified:

- Project name and Stage id.
- Required top-level JSON fields.
- `maxCodeBlockLength == 1000`.
- `motherNoiseLength >= maxCodeBlockLength`.
- Payload lengths include 200 and 300.
- Rate formula is exactly `K_payload/N_encoded`.
- Five rate examples are computed, not string-compared.
- BPSK mapping, hard decision, AWGN sigma, and LLR sign.
- `noiseGroupId`, `reuseNoiseAcrossSnr`, and decoder seed exclusion.
- Per-frame independent-noise principle is declared.
- Stop-rule values and AND/OR stop logic.
- LDPC interleaver prohibition and base AWGN interleaver disablement.
- Point/curve separation and coding gain placement.
- Checkpoint fields.
- Plot naming template and overwrite policy.
- Core definitions are present in both JSON and docs.

## 未通过项

None.

## Gate

Gate: PASS_COMMON_DEFINITION

## Git 范围检查

Executed:

```powershell
git status --short --branch
git diff --stat
git diff -- Task/Common
git ls-files --others --exclude-standard Task/Common
git status --porcelain=v1 Task/BCH Task/CC Task/LDPC
```

Results:

- Current branch: `stage01-common-definition`.
- Working tree: new untracked `Task/Common/` files only.
- `git diff --stat` and `git diff -- Task/Common` are empty because the Stage files are new and not staged or committed.
- `git ls-files --others --exclude-standard Task/Common` lists only Common-01 files and snapshot copies.
- `Task/BCH`, `Task/CC`, and `Task/LDPC` have no status output, so no out-of-scope edits were detected.

## Commit

Initial Stage commit:

```text
899c4c4 stage01: freeze common definitions
```

After this commit, audit metadata is updated to record the commit hash.
