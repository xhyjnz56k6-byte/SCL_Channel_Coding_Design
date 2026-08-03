cmake_minimum_required(VERSION 3.20)
project(s5_multichannel_comparison LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

set(REPO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../../..")

add_library(s5_core
    current/src/s5.cpp
    ${REPO_ROOT}/Task/Common/src/random_policy.cpp
    ${REPO_ROOT}/Task/Common/src/gaussian_noise.cpp
    ${REPO_ROOT}/Task/CC/shared/src/trellis.cpp
    ${REPO_ROOT}/Task/CC/shared/src/puncturing.cpp
    ${REPO_ROOT}/Task/CC/block/current/src/block_encoder.cpp
    ${REPO_ROOT}/Task/CC/block/current/src/soft_viterbi.cpp
    ${REPO_ROOT}/Task/LDPC/block/current/src/nr_tables.cpp
    ${REPO_ROOT}/Task/LDPC/block/current/src/s4_ldpc.cpp
)
target_include_directories(s5_core PUBLIC
    current/include
    ${REPO_ROOT}/Task/Common/include
    ${REPO_ROOT}/Task/CC/shared/include
    ${REPO_ROOT}/Task/CC/block/current/include
    ${REPO_ROOT}/Task/LDPC/block/current/include
)

add_executable(s5_runner current/src/s5_runner.cpp)
target_link_libraries(s5_runner PRIVATE s5_core)

add_executable(s5_unit_tests current/tests/test_s5.cpp)
target_link_libraries(s5_unit_tests PRIVATE s5_core)

add_executable(s5_stage12_cc_validation
    stages/stage12_known_erasure_cc_validation/cpp/src/stage12_cc_validation.cpp)
target_link_libraries(s5_stage12_cc_validation PRIVATE s5_core)

if(MSVC)
    target_compile_options(s5_core PRIVATE /O2 /W4)
else()
    target_compile_options(s5_core PRIVATE -O3 -Wall -Wextra -Wpedantic)
endif()

enable_testing()
add_test(NAME s5_unit_tests COMMAND s5_unit_tests)
