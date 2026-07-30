# Checkpoint 设计

每个 Case/SNR 独立目录；每 500 帧形成不可变 summary/sample chunk。checkpoint 通过 `.tmp -> flush/fsync -> os.replace` 原子更新，并记录每个 chunk SHA256。恢复前校验 config、code commit、Case、SNR、alpha、seed、nextFrameIndex 与所有 chunk hash。不同配置或损坏 chunk 会拒绝恢复。多个进程从不写同一文件。
