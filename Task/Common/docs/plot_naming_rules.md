# 图片和结果命名规则

## 图片命名模板

唯一模板：

```text
{stage}_{code}_{case}_{channel}_{decoder}_{metric}.png
```

示例：

```text
common08_uncoded_k300_awgn_hard_ber.png
formal_cc_k300_r12_awgn_hard_vs_soft_fer.png
formal_ldpc_k300_n576_awgn_bp_vs_nms_fer.png
```

禁止：

```text
figure1.png
result.png
plot.png
new_result.png
```

## 结果文件

点级结果：

```text
point_results.csv
```

每个 SNR 点一行。

曲线级结果：

```text
curve_summary.csv
```

用于目标 BER/FER、参考曲线交点、候选曲线交点、编码增益、插值方法和有效性标记。

元数据：

```text
run_metadata.json
```

trace：

```text
trace.csv
```

## trace 策略

```text
smoke: 保存前 10 帧完整 trace
prescan: 保存前 3 帧和前 10 个错误帧
formal: 默认关闭或仅保存错误帧摘要
```

## 防覆盖

默认：

```text
overwriteExistingResults = false
```

已有正式结果时必须拒绝静默覆盖。新结果应使用新的 runId、caseId、stage 目录或显式授权的覆盖参数。

