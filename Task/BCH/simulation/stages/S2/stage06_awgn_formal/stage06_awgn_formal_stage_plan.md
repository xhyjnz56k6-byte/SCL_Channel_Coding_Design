# stage06_awgn_formal 规格冻结

## 目标

对 stage02 冻结的 8 个 Case 各执行 5 个手工正式 AWGN 点，发布可复算的 BER、FER、
译码时延、checkpoint、分片清单、合并审计及 6 张正式 PNG。

## 非目标与范围

不做 prescan，不改变 stage01–stage05 契约，不执行多径。仅修改
`Task/BCH/simulation/stages/S2/stage06_awgn_formal/`；构建和明细结果位于本 Stage
的 build/results 生成目录。

## 正式停止规则

每点至少 5000 帧；达到 5000 帧后若累计误帧数不少于 200 则停止；否则继续，最多
50000 帧。停止原因只能是 `TARGET_FRAME_ERRORS_REACHED` 或 `MAX_FRAMES_REACHED`。

## Gate

40/40 点计数与公式复算、40 个 checkpoint、分片/合并审计及 6 张 300 dpi PNG 全部
通过后，必须真实输出 `PASS_STAGE06_AWGN_FORMAL` 和
`PASS_BCH_S2_AWGN_STAGE01_TO_STAGE06`。
