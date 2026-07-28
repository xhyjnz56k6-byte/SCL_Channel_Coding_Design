cmake_minimum_required(VERSION 3.20)
project(stage11_soft_quantization LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(REPO_ROOT "${CMAKE_CURRENT_LIST_DIR}/../../../../../..")
set(CC_ROOT "${REPO_ROOT}/Task/CC")
add_executable(stage11_soft_quantization_runner
    src/stage11_soft_quantization_runner.cpp
    "${CC_ROOT}/shared/src/trellis.cpp"
    "${CC_ROOT}/shared/src/puncturing.cpp"
    "${CC_ROOT}/block/current/src/block_encoder.cpp"
    "${CC_ROOT}/block/current/src/soft_viterbi.cpp"
    "${REPO_ROOT}/Task/Common/src/random_policy.cpp"
    "${REPO_ROOT}/Task/Common/src/gaussian_noise.cpp")
target_include_directories(stage11_soft_quantization_runner PRIVATE
    "${CC_ROOT}/shared/include" "${CC_ROOT}/block/current/include"
    "${REPO_ROOT}/Task/Common/include")
if(NOT MSVC)
  target_compile_options(stage11_soft_quantization_runner PRIVATE -O3 -Wall -Wextra -Wpedantic -Werror)
endif()
