cmake_minimum_required(VERSION 3.16)
project(stage15_interleaving_formal LANGUAGES CXX)
set(BCH_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../../../../..")
set(COMMON_ROOT "${BCH_ROOT}/../Common")
set(S1 "${CMAKE_CURRENT_SOURCE_DIR}/../../stage01_foundation/cpp")
set(S2 "${CMAKE_CURRENT_SOURCE_DIR}/../../stage02_case_contract/cpp")
set(S13 "${CMAKE_CURRENT_SOURCE_DIR}/../../stage13_burst_interleaving_validation/cpp")
add_library(stage15_block "${BCH_ROOT}/block/current/src/bch_block.cpp")
target_include_directories(stage15_block PUBLIC "${BCH_ROOT}/block/current/include" "${COMMON_ROOT}/include")
target_compile_features(stage15_block PUBLIC cxx_std_17)
add_library(stage15_segmented
 "${BCH_ROOT}/segmented/current/src/bch15_encoder.cpp"
 "${BCH_ROOT}/segmented/current/src/bch15_syndrome.cpp"
 "${BCH_ROOT}/segmented/current/src/bch15_lookup_table.cpp"
 "${BCH_ROOT}/segmented/current/src/bch15_lookup_decoder.cpp"
 "${BCH_ROOT}/segmented/current/src/bch15_segmented_adapter.cpp")
target_include_directories(stage15_segmented PUBLIC "${BCH_ROOT}/segmented/current/include" "${COMMON_ROOT}/include")
target_compile_features(stage15_segmented PUBLIC cxx_std_17)
add_library(stage15_support
 "${S1}/stage01_foundation_awgn.cpp" "${S2}/stage02_case_contract.cpp"
 "${S13}/stage13_burst_interleaving_validation_core.cpp"
 "${S13}/stage13_burst_interleaving_validation_simulation.cpp")
target_include_directories(stage15_support PUBLIC "${S1}" "${S2}" "${S13}")
target_link_libraries(stage15_support PUBLIC stage15_block stage15_segmented)
target_compile_features(stage15_support PUBLIC cxx_std_17)
add_executable(stage15_interleaving_formal_runner stage15_interleaving_formal_runner.cpp)
target_link_libraries(stage15_interleaving_formal_runner PRIVATE stage15_support)
enable_testing()
add_test(NAME stage15_interleaving_formal_cli_validation COMMAND stage15_interleaving_formal_runner)
set_tests_properties(stage15_interleaving_formal_cli_validation PROPERTIES WILL_FAIL TRUE)

