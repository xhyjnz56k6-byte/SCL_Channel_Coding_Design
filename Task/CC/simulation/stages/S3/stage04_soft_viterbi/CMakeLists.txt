cmake_minimum_required(VERSION 3.20)
project(stage04_soft_viterbi LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CC_ROOT "${CMAKE_CURRENT_LIST_DIR}/../../../..")
add_library(cc_stage04 STATIC
    "${CC_ROOT}/shared/src/trellis.cpp"
    "${CC_ROOT}/block/current/src/block_encoder.cpp"
    "${CC_ROOT}/block/current/src/hard_viterbi.cpp"
    "${CC_ROOT}/block/current/src/soft_viterbi.cpp"
)
target_include_directories(cc_stage04 PUBLIC
    "${CC_ROOT}/shared/include"
    "${CC_ROOT}/block/current/include"
)
if(MSVC)
    target_compile_options(cc_stage04 PRIVATE /W4 /permissive-)
else()
    target_compile_options(cc_stage04 PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_executable(stage04_soft_viterbi_tests tests/test_stage04_soft_viterbi.cpp)
target_link_libraries(stage04_soft_viterbi_tests PRIVATE cc_stage04)
enable_testing()
add_test(NAME stage04_soft_viterbi_tests COMMAND stage04_soft_viterbi_tests)
