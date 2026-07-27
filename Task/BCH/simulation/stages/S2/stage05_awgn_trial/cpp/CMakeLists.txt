cmake_minimum_required(VERSION 3.16)
project(stage05_awgn_trial LANGUAGES CXX)

set(BCH_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../../../../..")
set(COMMON_ROOT "${BCH_ROOT}/../Common")
set(STAGE01_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../../stage01_foundation/cpp")
set(STAGE02_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../../stage02_case_contract/cpp")

add_library(stage05_block_core "${BCH_ROOT}/block/current/src/bch_block.cpp")
target_include_directories(stage05_block_core PUBLIC "${BCH_ROOT}/block/current/include" "${COMMON_ROOT}/include")
target_compile_features(stage05_block_core PUBLIC cxx_std_17)

add_library(stage05_segmented_core
    "${BCH_ROOT}/segmented/current/src/bch15_encoder.cpp"
    "${BCH_ROOT}/segmented/current/src/bch15_syndrome.cpp"
    "${BCH_ROOT}/segmented/current/src/bch15_lookup_table.cpp"
    "${BCH_ROOT}/segmented/current/src/bch15_lookup_decoder.cpp"
    "${BCH_ROOT}/segmented/current/src/bch15_segmented_adapter.cpp")
target_include_directories(stage05_segmented_core PUBLIC "${BCH_ROOT}/segmented/current/include" "${COMMON_ROOT}/include")
target_compile_features(stage05_segmented_core PUBLIC cxx_std_17)

add_library(stage05_support
    "${STAGE01_ROOT}/stage01_foundation_awgn.cpp"
    "${STAGE02_ROOT}/stage02_case_contract.cpp")
target_include_directories(stage05_support PUBLIC "${STAGE01_ROOT}" "${STAGE02_ROOT}")
target_link_libraries(stage05_support PUBLIC stage05_block_core stage05_segmented_core)
target_compile_features(stage05_support PUBLIC cxx_std_17)

add_executable(stage05_awgn_trial_runner stage05_awgn_trial_runner.cpp)
target_link_libraries(stage05_awgn_trial_runner PRIVATE stage05_support)

enable_testing()
add_test(NAME stage05_awgn_trial_cli_validation COMMAND stage05_awgn_trial_runner)
set_tests_properties(stage05_awgn_trial_cli_validation PROPERTIES WILL_FAIL TRUE)
