# SNR 公式审计

CC `stage14_runner.cpp:522-523` 使用 `sigmaSquared=1/(2*10^(snr/10))`；
`frozen_config.csv` 与 `stage_plan.md` 均把横轴定义为 Es/N0，CSV 同时记录 `snrDb,esN0Db,ebN0Db,actualRate,sigmaSquared`，无内部冲突。
