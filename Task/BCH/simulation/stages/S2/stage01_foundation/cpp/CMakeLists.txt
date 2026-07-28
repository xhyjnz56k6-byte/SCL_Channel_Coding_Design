cmake_minimum_required(VERSION 3.16)
project(stage01_foundation LANGUAGES CXX)

add_library(stage01_foundation_lib
    stage01_foundation_awgn.cpp)
target_include_directories(stage01_foundation_lib PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
target_compile_features(stage01_foundation_lib PUBLIC cxx_std_17)

add_executable(stage01_foundation_test
    stage01_foundation_test.cpp)
target_link_libraries(stage01_foundation_test PRIVATE stage01_foundation_lib)

add_executable(stage01_foundation_export
    stage01_foundation_export.cpp)
target_link_libraries(stage01_foundation_export PRIVATE stage01_foundation_lib)

enable_testing()
add_test(NAME stage01_foundation_unit COMMAND stage01_foundation_test)
