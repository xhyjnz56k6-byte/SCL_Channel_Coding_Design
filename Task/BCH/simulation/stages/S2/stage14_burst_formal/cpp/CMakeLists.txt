cmake_minimum_required(VERSION 3.16)
project(stage14_burst_formal LANGUAGES CXX)

set(BCH_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../../../../..")
set(COMMON_ROOT "${BCH_ROOT}/../Common")
set(STAGE01_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../../stage01_foundation/cpp")
set(STAGE02_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../../stage02_case_contract/cpp")
set(STAGE13_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../../stage13_burst_interleaving_validation/cpp")

add_library(stage14_block_core "${BCH_ROOT}/block/current/src/bch_block.cpp")
target_include_directories(stage14_block_core PUBLIC
    "${BCH_ROOT}/block/current/include" "${COMMON_ROOT}/include")
target_compile_features(stage14_block_core PUBLIC cxx_std_17)

add_library(stage14_segmented_core
    "${BCH_ROOT}/segmented/current/src/bch15_encoder.cpp"
    "${BCH_ROOT}/segmented/current/src/bch15_syndrome.cpp"
    "${BCH_ROOT}/segmented/current/src/bch15_lookup_table.cpp"
    "${BCH_ROOT}/segmented/current/src/bch15_lookup_decoder.cpp"
    "${BCH_ROOT}/segmented/current/src/bch15_segmented_adapter.cpp")
target_include_directories(stage14_segmented_core PUBLIC
    "${BCH_ROOT}/segmented/current/include" "${COMMON_ROOT}/include")
target_compile_features(stage14_segmented_core PUBLIC cxx_std_17)

add_library(stage14_support
    "${STAGE01_ROOT}/stage01_foundation_awgn.cpp"
    "${STAGE02_ROOT}/stage02_case_contract.cpp"
    "${STAGE13_ROOT}/stage13_burst_interleaving_validation_core.cpp"
    "${STAGE13_ROOT}/stage13_burst_interleaving_validation_simulation.cpp")
target_include_directories(stage14_support PUBLIC
    "${STAGE01_ROOT}" "${STAGE02_ROOT}" "${STAGE13_ROOT}")
target_link_libraries(stage14_support PUBLIC
    stage14_block_core stage14_segmented_core)
target_compile_features(stage14_support PUBLIC cxx_std_17)

add_executable(stage14_burst_formal_runner
    stage14_burst_formal_runner.cpp)
target_link_libraries(stage14_burst_formal_runner PRIVATE stage14_support)

enable_testing()
add_test(NAME stage14_burst_formal_cli_validation
    COMMAND stage14_burst_formal_runner)
set_tests_properties(stage14_burst_formal_cli_validation
    PROPERTIES WILL_FAIL TRUE)

