cmake_minimum_required(VERSION 3.20)
project(stage03_hard_viterbi LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CC_ROOT "${CMAKE_CURRENT_LIST_DIR}/../../../..")

add_library(cc_stage03 STATIC
    "${CC_ROOT}/shared/src/trellis.cpp"
    "${CC_ROOT}/block/current/src/block_encoder.cpp"
    "${CC_ROOT}/block/current/src/hard_viterbi.cpp"
)
target_include_directories(cc_stage03 PUBLIC
    "${CC_ROOT}/shared/include"
    "${CC_ROOT}/block/current/include"
)
if(MSVC)
    target_compile_options(cc_stage03 PRIVATE /W4 /permissive-)
else()
    target_compile_options(cc_stage03 PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()

add_executable(stage03_hard_viterbi_tests tests/test_stage03_hard_viterbi.cpp)
target_link_libraries(stage03_hard_viterbi_tests PRIVATE cc_stage03)
enable_testing()
add_test(NAME stage03_hard_viterbi_tests COMMAND stage03_hard_viterbi_tests)
