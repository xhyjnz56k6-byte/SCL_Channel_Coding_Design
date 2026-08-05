# Stage00 已知问题

- 当前分支名 `S7-Comparision` 不符合建议格式并保留拼写错误；用户已明确指定使用，记录为例外。
- 历史仓库存在已跟踪的 build、exe、obj、pycache 等生成内容；S7 不删除旧历史，但禁止新增。
- MATLAB 命令和所需工具箱尚未实测，必须在 Stage08 前验证。
- LDPC 历史基线只兼容普通 BPSK+AWGN，不兼容 S7 主突发信道，只能用于独立参考表。
- 已知连续擦除和未知连续强干扰尚未纳入主实现；它们不是主 Formal，若未做将作为扩展未完成项保留。
- 尚未形成 Git functional range，因为用户未要求 commit；不得伪造 contentCommit。

