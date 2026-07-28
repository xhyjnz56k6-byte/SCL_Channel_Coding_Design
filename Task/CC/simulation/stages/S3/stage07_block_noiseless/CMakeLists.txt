cmake_minimum_required(VERSION 3.20)
project(stage07_block_noiseless LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CC_ROOT "${CMAKE_CURRENT_LIST_DIR}/../../../..")
add_executable(stage07_block_noiseless_tests
    tests/test_stage07_block_noiseless.cpp
    "${CC_ROOT}/shared/src/trellis.cpp"
    "${CC_ROOT}/shared/src/puncturing.cpp"
    "${CC_ROOT}/block/current/src/block_encoder.cpp"
    "${CC_ROOT}/block/current/src/hard_viterbi.cpp"
    "${CC_ROOT}/block/current/src/soft_viterbi.cpp"
)
target_include_directories(stage07_block_noiseless_tests PRIVATE
    "${CC_ROOT}/shared/include" "${CC_ROOT}/block/current/include")
if(NOT MSVC)
    target_compile_options(stage07_block_noiseless_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
enable_testing()
add_test(NAME stage07_block_noiseless_tests
    COMMAND stage07_block_noiseless_tests "${CMAKE_CURRENT_LIST_DIR}/results")
