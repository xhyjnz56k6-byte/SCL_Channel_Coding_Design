cmake_minimum_required(VERSION 3.20)
project(s4_ldpc LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_library(s4_ldpc_core
    current/src/nr_tables.cpp
    current/src/s4_ldpc.cpp
)
target_include_directories(s4_ldpc_core PUBLIC current/include)

add_executable(s4_ldpc_runner current/src/main.cpp)
target_link_libraries(s4_ldpc_runner PRIVATE s4_ldpc_core)

add_executable(s4_ldpc_unit_tests current/tests/unit_tests.cpp)
target_link_libraries(s4_ldpc_unit_tests PRIVATE s4_ldpc_core)

if(MSVC)
    target_compile_options(s4_ldpc_core PRIVATE /O2 /W4)
else()
    target_compile_options(s4_ldpc_core PRIVATE -O3 -Wall -Wextra -Wpedantic)
endif()

enable_testing()
add_test(NAME s4_ldpc_unit_tests COMMAND s4_ldpc_unit_tests)
