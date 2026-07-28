cmake_minimum_required(VERSION 3.20)
project(stage05_matlab_reference LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CC_ROOT "${CMAKE_CURRENT_LIST_DIR}/../../../..")
add_library(cc_stage05 STATIC
    "${CC_ROOT}/shared/src/trellis.cpp"
    "${CC_ROOT}/block/current/src/block_encoder.cpp"
    "${CC_ROOT}/block/current/src/hard_viterbi.cpp"
    "${CC_ROOT}/block/current/src/soft_viterbi.cpp"
)
target_include_directories(cc_stage05 PUBLIC "${CC_ROOT}/shared/include" "${CC_ROOT}/block/current/include")
if(MSVC)
    target_compile_options(cc_stage05 PRIVATE /W4 /permissive-)
else()
    target_compile_options(cc_stage05 PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_executable(stage05_reference_runner tests/stage05_reference_runner.cpp)
target_link_libraries(stage05_reference_runner PRIVATE cc_stage05)
