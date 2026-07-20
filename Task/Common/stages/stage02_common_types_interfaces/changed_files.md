# Changed Files

## Added Files

### `Task/Common/CMakeLists.txt`

- 类型：新增
- 作用：定义 `common_foundation` interface target and Stage02 test executable.
- 原因：Common-02 needs an isolated build entry.
- 是否影响旧行为：否。

### `Task/Common/include/common/*.hpp`

- 类型：新增
- 作用：定义 `Bit`、`CodeLengths`、`PayloadFrame`、`DecoderInput` variant、`DecodeResult`、checkpoint/result records, channel/encoder/decoder/frame-pool interfaces.
- 原因：冻结公共类型和接口骨架。
- 关键定义：`computeCodeRate`、`validateCodeLengths`、`validatePayloadFrame`、`IChannelEncoder`、`IChannelDecoder`、`IChannel`、`IFramePoolReader`。
- 是否影响旧行为：否。

### `Task/Common/src/common_interfaces.cpp`

- 类型：新增
- 作用：编译公共头文件，不提供算法实现。
- 原因：确保 headers 可以独立编译。
- 是否影响旧行为：否。

### `Task/Common/tests/stage02/test_common02_types_interfaces.cpp`

- 类型：新增
- 作用：测试 bit 类型、长度校验、五个码率样例、PayloadFrame、DecoderInput variant、virtual destructor、checkpoint SNR 字段。
- 是否影响旧行为：否。

### `Task/Common/scripts/build_common02.py`

- 类型：新增
- 作用：用 `g++ -std=c++17` 构建 Stage02 测试。
- 是否影响旧行为：否。

### `Task/Common/scripts/check_common02.py`

- 类型：新增
- 作用：自动执行构建、测试、负向测试、禁止 include/实现扫描、snapshot SHA、Git diff 边界检查。
- 是否影响旧行为：否。

### `Task/Common/stages/stage02_common_types_interfaces/`

- 类型：新增
- 作用：Stage02 审计目录。
- 是否影响旧行为：否。

## Modified Files

None outside the added Common-02 files.

## Deleted Files

None in this Stage.

