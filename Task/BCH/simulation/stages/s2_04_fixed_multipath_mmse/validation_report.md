# S2-04 Fixed Multipath MMSE Validation Report

- 正式点数=145，实际处理帧数=2653721。
- stopReason 分布={'TARGET_FRAME_ERRORS_REACHED': 115, 'MAX_FRAMES_REACHED': 30}。
- 多径五 Case 均真实夹住 FER=1e-1/1e-2/1e-3；历史 AWGN 未夹住的两项明确无效且无外推。
- 200/300-bit checkpoint-resume 与三分片原始计数一致。
- MATLAB 15 个 Case-point、1500 帧：硬判决/payload/frame mismatch=0。
- PNG=24，figure-data CSV=24，非 PNG=0。

Gate：`PASS_BCH_S2_04_FIXED_MULTIPATH_MMSE`

远端功能提交已验证；`mergeStatus=NOT_MERGED`。
