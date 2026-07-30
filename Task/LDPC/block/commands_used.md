# 复现命令

1. 生成只读迁移表：`python scripts/generate_nr_tables.py ...`
2. Release 构建：`cmake -G "MinGW Makefiles" ...`，`cmake --build ...`
3. 测试：`ctest --output-on-failure`
4. selector/validate/fixture：`s4_ldpc_runner selector|validate|fixture`
5. Stage10：alpha=0.65,0.75,0.85,0.95；minFrames=200,targetFrameErrors=40,maxFrames=600。
6. Stage11：局部 alpha=0.80,0.90,1.00；独立 runId。
7. Stage12：minFrames=100,targetFrameErrors=30,maxFrames=500；frameIndex 从 10000 开始；未启动 formal。
