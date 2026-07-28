cmake_minimum_required(VERSION 3.16)
project(stage13_burst_interleaving_validation LANGUAGES CXX)

set(BCH_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../../../../..")
set(COMMON_ROOT "${BCH_ROOT}/../Common")
set(STAGE01_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../../stage01_foundation/cpp")
set(STAGE02_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../../stage02_case_contract/cpp")

add_library(stage13_block_core "${BCH_ROOT}/block/current/src/bch_block.cpp")
target_include_directories(stage13_block_core PUBLIC
    "${BCH_ROOT}/block/current/include" "${COMMON_ROOT}/include")
target_compile_features(stage13_block_core PUBLIC cxx_std_17)

add_library(stage13_segmented_core
    "${BCH_ROOT}/segmented/current/src/bch15_encoder.cpp"
    "${BCH_ROOT}/segmented/current/src/bch15_syndrome.cpp"
    "${BCH_ROOT}/segmented/current/src/bch15_lookup_table.cpp"
    "${BCH_ROOT}/segmented/current/src/bch15_lookup_decoder.cpp"
    "${BCH_ROOT}/segmented/current/src/bch15_segmented_adapter.cpp")
target_include_directories(stage13_segmented_core PUBLIC
    "${BCH_ROOT}/segmented/current/include" "${COMMON_ROOT}/include")
target_compile_features(stage13_segmented_core PUBLIC cxx_std_17)

add_library(stage13_support
    "${STAGE01_ROOT}/stage01_foundation_awgn.cpp"
    "${STAGE02_ROOT}/stage02_case_contract.cpp"
    stage13_burst_interleaving_validation_core.cpp
    stage13_burst_interleaving_validation_simulation.cpp)
target_include_directories(stage13_support PUBLIC
    "${CMAKE_CURRENT_SOURCE_DIR}" "${STAGE01_ROOT}" "${STAGE02_ROOT}")
target_link_libraries(stage13_support PUBLIC
    stage13_block_core stage13_segmented_core)
target_compile_features(stage13_support PUBLIC cxx_std_17)

add_executable(stage13_burst_interleaving_validation_test
    stage13_burst_interleaving_validation_test.cpp)
target_link_libraries(stage13_burst_interleaving_validation_test
    PRIVATE stage13_support)

add_executable(stage13_burst_interleaving_validation_runner
    stage13_burst_interleaving_validation_runner.cpp)
target_link_libraries(stage13_burst_interleaving_validation_runner
    PRIVATE stage13_support)

enable_testing()
add_test(NAME stage13_burst_interleaving_validation_unit
    COMMAND stage13_burst_interleaving_validation_test)
