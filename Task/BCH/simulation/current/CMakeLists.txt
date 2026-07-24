cmake_minimum_required(VERSION 3.16)
project(BchGroup4Simulation LANGUAGES CXX)

set(COMMON_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../../../Common")
add_library(common_bch_simulation STATIC
    ${COMMON_ROOT}/src/random_policy.cpp
    ${COMMON_ROOT}/src/gaussian_noise.cpp
    ${COMMON_ROOT}/src/modulation.cpp
    ${COMMON_ROOT}/src/awgn_channel.cpp
    ${COMMON_ROOT}/src/demodulation.cpp
    ${COMMON_ROOT}/src/simulation_metrics.cpp
    ${COMMON_ROOT}/src/simulation_control.cpp
    ${COMMON_ROOT}/src/checkpoint.cpp)
target_include_directories(common_bch_simulation PUBLIC ${COMMON_ROOT}/include)
target_compile_features(common_bch_simulation PUBLIC cxx_std_17)

add_subdirectory("${CMAKE_CURRENT_SOURCE_DIR}/../../segmented/current" segmented_core)
add_subdirectory("${CMAKE_CURRENT_SOURCE_DIR}/../../block/current" block_core)

add_library(bch_case_adapter
    src/bch_case_adapter.cpp
    src/bch_awgn_simulation.cpp
    src/bch_multipath_simulation.cpp
    src/fixed_multipath_mmse.cpp)
target_include_directories(bch_case_adapter PUBLIC include)
target_link_libraries(bch_case_adapter PUBLIC bch15_encoder bch_block common_bch_simulation)
target_compile_features(bch_case_adapter PUBLIC cxx_std_17)

add_executable(test_bch11_noiseless tests/test_bch11_noiseless.cpp)
target_link_libraries(test_bch11_noiseless PRIVATE bch_case_adapter)
add_executable(test_bch12_awgn tests/test_bch12_awgn.cpp)
target_link_libraries(test_bch12_awgn PRIVATE bch_case_adapter)
add_executable(test_bch_s2_mmse tests/test_bch_s2_mmse.cpp)
target_link_libraries(test_bch_s2_mmse PRIVATE bch_case_adapter)
add_executable(bch_awgn_runner src/bch_awgn_runner.cpp)
target_link_libraries(bch_awgn_runner PRIVATE bch_case_adapter)
add_executable(bch_multipath_runner src/bch_multipath_runner.cpp)
target_link_libraries(bch_multipath_runner PRIVATE bch_case_adapter)
add_executable(export_bch_s2_matlab_vectors tests/export_bch_s2_matlab_vectors.cpp)
target_link_libraries(export_bch_s2_matlab_vectors PRIVATE bch_case_adapter)

enable_testing()
if (DEFINED BCH_K200_MANIFEST AND DEFINED BCH_K300_MANIFEST)
    add_test(NAME bch11_common_noiseless COMMAND test_bch11_noiseless
        ${BCH_K200_MANIFEST} ${BCH_K300_MANIFEST} ${CMAKE_CURRENT_BINARY_DIR}/bch11_outputs)
endif()
add_test(NAME bch12_awgn_unit COMMAND test_bch12_awgn)
add_test(NAME bch_s2_mmse_unit COMMAND test_bch_s2_mmse)
