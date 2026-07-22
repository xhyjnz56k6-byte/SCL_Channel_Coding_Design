cmake_minimum_required(VERSION 3.16)
project(BchGroup4Simulation LANGUAGES CXX)

set(COMMON_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../../../Common")
add_library(common_bch_simulation STATIC
    ${COMMON_ROOT}/src/modulation.cpp
    ${COMMON_ROOT}/src/demodulation.cpp
    ${COMMON_ROOT}/src/simulation_metrics.cpp)
target_include_directories(common_bch_simulation PUBLIC ${COMMON_ROOT}/include)
target_compile_features(common_bch_simulation PUBLIC cxx_std_17)

add_subdirectory("${CMAKE_CURRENT_SOURCE_DIR}/../../segmented/current" segmented_core)
add_subdirectory("${CMAKE_CURRENT_SOURCE_DIR}/../../block/current" block_core)

add_library(bch_case_adapter src/bch_case_adapter.cpp)
target_include_directories(bch_case_adapter PUBLIC include)
target_link_libraries(bch_case_adapter PUBLIC bch15_encoder bch_block common_bch_simulation)
target_compile_features(bch_case_adapter PUBLIC cxx_std_17)

add_executable(test_bch11_noiseless tests/test_bch11_noiseless.cpp)
target_link_libraries(test_bch11_noiseless PRIVATE bch_case_adapter)

enable_testing()
if (DEFINED BCH_K200_MANIFEST AND DEFINED BCH_K300_MANIFEST)
    add_test(NAME bch11_common_noiseless COMMAND test_bch11_noiseless
        ${BCH_K200_MANIFEST} ${BCH_K300_MANIFEST} ${CMAKE_CURRENT_BINARY_DIR}/bch11_outputs)
endif()
