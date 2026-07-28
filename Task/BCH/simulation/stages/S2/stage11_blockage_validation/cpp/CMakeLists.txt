cmake_minimum_required(VERSION 3.16)
project(stage11_blockage_validation LANGUAGES CXX)
set(BCH_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../../../../..")
set(COMMON_ROOT "${BCH_ROOT}/../Common")
set(STAGE01_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../../stage01_foundation/cpp")
set(STAGE02_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../../stage02_case_contract/cpp")
add_library(stage11_block_core "${BCH_ROOT}/block/current/src/bch_block.cpp")
target_include_directories(stage11_block_core PUBLIC "${BCH_ROOT}/block/current/include" "${COMMON_ROOT}/include")
target_compile_features(stage11_block_core PUBLIC cxx_std_17)
add_library(stage11_segmented_core
 "${BCH_ROOT}/segmented/current/src/bch15_encoder.cpp"
 "${BCH_ROOT}/segmented/current/src/bch15_syndrome.cpp"
 "${BCH_ROOT}/segmented/current/src/bch15_lookup_table.cpp"
 "${BCH_ROOT}/segmented/current/src/bch15_lookup_decoder.cpp"
 "${BCH_ROOT}/segmented/current/src/bch15_segmented_adapter.cpp")
target_include_directories(stage11_segmented_core PUBLIC "${BCH_ROOT}/segmented/current/include" "${COMMON_ROOT}/include")
target_compile_features(stage11_segmented_core PUBLIC cxx_std_17)
add_library(stage11_support "${STAGE01_ROOT}/stage01_foundation_awgn.cpp"
                            "${STAGE02_ROOT}/stage02_case_contract.cpp")
target_include_directories(stage11_support PUBLIC "${STAGE01_ROOT}" "${STAGE02_ROOT}")
target_link_libraries(stage11_support PUBLIC stage11_block_core stage11_segmented_core)
target_compile_features(stage11_support PUBLIC cxx_std_17)
add_executable(stage11_blockage_validation_runner stage11_blockage_validation_runner.cpp)
target_link_libraries(stage11_blockage_validation_runner PRIVATE stage11_support)
enable_testing()
add_test(NAME stage11_blockage_validation COMMAND stage11_blockage_validation_runner
 "${CMAKE_CURRENT_SOURCE_DIR}/../results")
