# Known issues

Zero-error points are retained as 0 in CSV and omitted on log axes. Target FER loss is unavailable where adjacent nonzero measured points do not bracket the target. No unified robustness score is produced.

Stage12交织结果仅为diagnostic_only，未混入Stage11或Aggregate。推荐结论仅适用于冻结S5模型；目标FER未覆盖时明确降级为6–10 dB实测FER比较，不能写成满足工程门限。
