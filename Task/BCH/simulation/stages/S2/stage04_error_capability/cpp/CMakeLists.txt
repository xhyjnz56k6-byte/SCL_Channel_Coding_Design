cmake_minimum_required(VERSION 3.16)
project(stage04_error_capability LANGUAGES CXX)

set(BCH_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../../../../..")
set(COMMON_ROOT "${BCH_ROOT}/../Common")
set(STAGE02_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../../stage02_case_contract/cpp")

add_library(stage04_block_core "${BCH_ROOT}/block/current/src/bch_block.cpp")
target_include_directories(stage04_block_core PUBLIC "${BCH_ROOT}/block/current/include" "${COMMON_ROOT}/include")
target_compile_features(stage04_block_core PUBLIC cxx_std_17)

add_library(stage04_segmented_core
    "${BCH_ROOT}/segmented/current/src/bch15_encoder.cpp"
    "${BCH_ROOT}/segmented/current/src/bch15_syndrome.cpp"
    "${BCH_ROOT}/segmented/current/src/bch15_lookup_table.cpp"
    "${BCH_ROOT}/segmented/current/src/bch15_lookup_decoder.cpp"
    "${BCH_ROOT}/segmented/current/src/bch15_segmented_adapter.cpp")
target_include_directories(stage04_segmented_core PUBLIC "${BCH_ROOT}/segmented/current/include" "${COMMON_ROOT}/include")
target_compile_features(stage04_segmented_core PUBLIC cxx_std_17)

add_library(stage04_contract "${STAGE02_ROOT}/stage02_case_contract.cpp")
target_include_directories(stage04_contract PUBLIC "${STAGE02_ROOT}")
target_link_libraries(stage04_contract PUBLIC stage04_block_core stage04_segmented_core)
target_compile_features(stage04_contract PUBLIC cxx_std_17)

add_executable(stage04_error_capability_runner stage04_error_capability_runner.cpp)
target_link_libraries(stage04_error_capability_runner PRIVATE stage04_contract)

if (NOT DEFINED STAGE04_OUTPUT_DIR)
    set(STAGE04_OUTPUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/stage04_error_capability_results")
endif()
enable_testing()
add_test(NAME stage04_error_capability_gate
    COMMAND stage04_error_capability_runner "${STAGE04_OUTPUT_DIR}")
