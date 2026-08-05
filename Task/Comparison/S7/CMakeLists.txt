cmake_minimum_required(VERSION 3.20)
project(s7_interleaving_burst_comparison LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(REPO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../../..")

add_library(s7_core
    current/src/s7.cpp
    ${REPO_ROOT}/Task/BCH/segmented/current/src/bch15_encoder.cpp
    ${REPO_ROOT}/Task/BCH/segmented/current/src/bch15_syndrome.cpp
    ${REPO_ROOT}/Task/BCH/segmented/current/src/bch15_lookup_table.cpp
    ${REPO_ROOT}/Task/BCH/segmented/current/src/bch15_lookup_decoder.cpp
    ${REPO_ROOT}/Task/BCH/segmented/current/src/bch15_segmented_adapter.cpp
    ${REPO_ROOT}/Task/CC/shared/src/trellis.cpp
    ${REPO_ROOT}/Task/CC/block/current/src/block_encoder.cpp
    ${REPO_ROOT}/Task/CC/block/current/src/soft_viterbi.cpp)

target_include_directories(s7_core PUBLIC
    current/include
    ${REPO_ROOT}/Task/Common/include
    ${REPO_ROOT}/Task/BCH/segmented/current/include
    ${REPO_ROOT}/Task/CC/shared/include
    ${REPO_ROOT}/Task/CC/block/current/include)

add_executable(s7_unit_tests current/tests/test_s7.cpp)
target_link_libraries(s7_unit_tests PRIVATE s7_core)

add_executable(s7_smoke_export current/src/s7_smoke_export.cpp)
target_link_libraries(s7_smoke_export PRIVATE s7_core)

add_executable(s7_prescan current/src/s7_prescan.cpp)
target_link_libraries(s7_prescan PRIVATE s7_core)

add_executable(s7_formal_runner current/src/s7_formal_runner.cpp)
target_link_libraries(s7_formal_runner PRIVATE s7_core)

add_executable(s7_all_start_runner current/src/s7_all_start_runner.cpp)
target_link_libraries(s7_all_start_runner PRIVATE s7_core)

if(MSVC)
    target_compile_options(s7_core PRIVATE /O2 /W4)
else()
    target_compile_options(s7_core PRIVATE -O2 -Wall -Wextra -Wpedantic)
endif()

enable_testing()
add_test(NAME s7_unit_tests COMMAND s7_unit_tests)
