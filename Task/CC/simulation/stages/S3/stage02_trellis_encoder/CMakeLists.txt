cmake_minimum_required(VERSION 3.20)
project(stage02_trellis_encoder LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

set(CC_ROOT "${CMAKE_CURRENT_LIST_DIR}/../../../..")

add_library(cc_stage02 STATIC
    "${CC_ROOT}/shared/src/trellis.cpp"
    "${CC_ROOT}/block/current/src/block_encoder.cpp"
)
target_include_directories(cc_stage02 PUBLIC
    "${CC_ROOT}/shared/include"
    "${CC_ROOT}/block/current/include"
)

if(MSVC)
    target_compile_options(cc_stage02 PRIVATE /W4 /permissive-)
else()
    target_compile_options(cc_stage02 PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()

add_executable(stage02_trellis_encoder_tests tests/test_stage02_trellis_encoder.cpp)
target_link_libraries(stage02_trellis_encoder_tests PRIVATE cc_stage02)

enable_testing()
add_test(NAME stage02_trellis_encoder_tests COMMAND stage02_trellis_encoder_tests)
