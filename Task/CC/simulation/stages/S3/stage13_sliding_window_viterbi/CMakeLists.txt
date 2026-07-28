cmake_minimum_required(VERSION 3.20)
project(stage13_sliding_window_viterbi LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 17)
set(REPO_ROOT "${CMAKE_CURRENT_LIST_DIR}/../../../../../..")
set(CC_ROOT "${REPO_ROOT}/Task/CC")
add_executable(stage13_runner src/stage13_runner.cpp
 "${CC_ROOT}/shared/src/trellis.cpp" "${CC_ROOT}/shared/src/puncturing.cpp"
 "${CC_ROOT}/block/current/src/block_encoder.cpp" "${CC_ROOT}/block/current/src/soft_viterbi.cpp"
 "${CC_ROOT}/block/current/src/hard_viterbi.cpp" "${REPO_ROOT}/Task/Common/src/random_policy.cpp"
 "${REPO_ROOT}/Task/Common/src/gaussian_noise.cpp")
target_include_directories(stage13_runner PRIVATE "${CC_ROOT}/shared/include" "${CC_ROOT}/block/current/include" "${REPO_ROOT}/Task/Common/include")
if(NOT MSVC)
 target_compile_options(stage13_runner PRIVATE -O3 -Wall -Wextra -Wpedantic -Werror)
endif()
