cmake_minimum_required(VERSION 3.16)
project(stage06_awgn_formal LANGUAGES CXX)

set(BCH_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../../../../..")
set(COMMON_ROOT "${BCH_ROOT}/../Common")
set(STAGE01_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../../stage01_foundation/cpp")
set(STAGE02_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../../stage02_case_contract/cpp")

add_library(stage06_block_core "${BCH_ROOT}/block/current/src/bch_block.cpp")
target_include_directories(stage06_block_core PUBLIC "${BCH_ROOT}/block/current/include" "${COMMON_ROOT}/include")
target_compile_features(stage06_block_core PUBLIC cxx_std_17)

add_library(stage06_segmented_core
    "${BCH_ROOT}/segmented/current/src/bch15_encoder.cpp"
    "${BCH_ROOT}/segmented/current/src/bch15_syndrome.cpp"
    "${BCH_ROOT}/segmented/current/src/bch15_lookup_table.cpp"
    "${BCH_ROOT}/segmented/current/src/bch15_lookup_decoder.cpp"
    "${BCH_ROOT}/segmented/current/src/bch15_segmented_adapter.cpp")
target_include_directories(stage06_segmented_core PUBLIC "${BCH_ROOT}/segmented/current/include" "${COMMON_ROOT}/include")
target_compile_features(stage06_segmented_core PUBLIC cxx_std_17)

add_library(stage06_support "${STAGE01_ROOT}/stage01_foundation_awgn.cpp"
                           "${STAGE02_ROOT}/stage02_case_contract.cpp")
target_include_directories(stage06_support PUBLIC "${STAGE01_ROOT}" "${STAGE02_ROOT}")
target_link_libraries(stage06_support PUBLIC stage06_block_core stage06_segmented_core)
target_compile_features(stage06_support PUBLIC cxx_std_17)

add_executable(stage06_awgn_formal_runner stage06_awgn_formal_runner.cpp)
target_link_libraries(stage06_awgn_formal_runner PRIVATE stage06_support)

enable_testing()
add_test(NAME stage06_awgn_formal_cli_validation COMMAND stage06_awgn_formal_runner)
set_tests_properties(stage06_awgn_formal_cli_validation PROPERTIES WILL_FAIL TRUE)
