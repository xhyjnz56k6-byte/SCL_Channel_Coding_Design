cmake_minimum_required(VERSION 3.16)
project(stage03_noiseless LANGUAGES CXX)

set(BCH_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../../../../..")
set(COMMON_ROOT "${BCH_ROOT}/../Common")
set(STAGE01_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../../stage01_foundation/cpp")
set(STAGE02_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../../stage02_case_contract/cpp")

add_library(stage03_block_core "${BCH_ROOT}/block/current/src/bch_block.cpp")
target_include_directories(stage03_block_core PUBLIC "${BCH_ROOT}/block/current/include" "${COMMON_ROOT}/include")
target_compile_features(stage03_block_core PUBLIC cxx_std_17)

add_library(stage03_segmented_core
    "${BCH_ROOT}/segmented/current/src/bch15_encoder.cpp"
    "${BCH_ROOT}/segmented/current/src/bch15_syndrome.cpp"
    "${BCH_ROOT}/segmented/current/src/bch15_lookup_table.cpp"
    "${BCH_ROOT}/segmented/current/src/bch15_lookup_decoder.cpp"
    "${BCH_ROOT}/segmented/current/src/bch15_segmented_adapter.cpp")
target_include_directories(stage03_segmented_core PUBLIC "${BCH_ROOT}/segmented/current/include" "${COMMON_ROOT}/include")
target_compile_features(stage03_segmented_core PUBLIC cxx_std_17)

add_library(stage03_support
    "${STAGE01_ROOT}/stage01_foundation_awgn.cpp"
    "${STAGE02_ROOT}/stage02_case_contract.cpp")
target_include_directories(stage03_support PUBLIC "${STAGE01_ROOT}" "${STAGE02_ROOT}")
target_link_libraries(stage03_support PUBLIC stage03_block_core stage03_segmented_core)
target_compile_features(stage03_support PUBLIC cxx_std_17)

add_executable(stage03_noiseless_runner stage03_noiseless_runner.cpp)
target_link_libraries(stage03_noiseless_runner PRIVATE stage03_support)

if (NOT DEFINED STAGE03_OUTPUT_DIR)
    set(STAGE03_OUTPUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/stage03_noiseless_results")
endif()
enable_testing()
add_test(NAME stage03_noiseless_gate COMMAND stage03_noiseless_runner "${STAGE03_OUTPUT_DIR}")
