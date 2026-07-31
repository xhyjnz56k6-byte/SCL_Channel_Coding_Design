cmake_minimum_required(VERSION 3.20)
project(stage06_puncturing LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CC_ROOT "${CMAKE_CURRENT_LIST_DIR}/../../../..")
add_executable(stage06_puncturing_tests
    tests/test_stage06_puncturing.cpp
    "${CC_ROOT}/shared/src/trellis.cpp"
    "${CC_ROOT}/shared/src/puncturing.cpp"
    "${CC_ROOT}/block/current/src/block_encoder.cpp"
    "${CC_ROOT}/block/current/src/hard_viterbi.cpp"
    "${CC_ROOT}/block/current/src/soft_viterbi.cpp"
)
target_include_directories(stage06_puncturing_tests PRIVATE
    "${CC_ROOT}/shared/include" "${CC_ROOT}/block/current/include")
if(NOT MSVC)
    target_compile_options(stage06_puncturing_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
enable_testing()
add_test(
    NAME stage06_puncturing_tests
    COMMAND stage06_puncturing_tests "${CMAKE_CURRENT_LIST_DIR}/results"
)
