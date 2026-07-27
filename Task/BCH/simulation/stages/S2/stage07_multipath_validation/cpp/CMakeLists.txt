cmake_minimum_required(VERSION 3.16)
project(stage07_multipath_validation LANGUAGES CXX)

set(BCH_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../../../../..")
set(COMMON_ROOT "${BCH_ROOT}/../Common")
set(STAGE01 "${CMAKE_CURRENT_SOURCE_DIR}/../../stage01_foundation/cpp")
set(STAGE02 "${CMAKE_CURRENT_SOURCE_DIR}/../../stage02_case_contract/cpp")

add_library(stage07_block_core "${BCH_ROOT}/block/current/src/bch_block.cpp")
target_include_directories(stage07_block_core PUBLIC
    "${BCH_ROOT}/block/current/include" "${COMMON_ROOT}/include")
target_compile_features(stage07_block_core PUBLIC cxx_std_17)

add_library(stage07_segmented_core
    "${BCH_ROOT}/segmented/current/src/bch15_encoder.cpp"
    "${BCH_ROOT}/segmented/current/src/bch15_syndrome.cpp"
    "${BCH_ROOT}/segmented/current/src/bch15_lookup_table.cpp"
    "${BCH_ROOT}/segmented/current/src/bch15_lookup_decoder.cpp"
    "${BCH_ROOT}/segmented/current/src/bch15_segmented_adapter.cpp")
target_include_directories(stage07_segmented_core PUBLIC
    "${BCH_ROOT}/segmented/current/include" "${COMMON_ROOT}/include")
target_compile_features(stage07_segmented_core PUBLIC cxx_std_17)

add_library(stage07_multipath_validation_lib
    "${STAGE01}/stage01_foundation_awgn.cpp"
    "${STAGE02}/stage02_case_contract.cpp"
    stage07_multipath_validation_core.cpp)
target_include_directories(stage07_multipath_validation_lib PUBLIC
    "${CMAKE_CURRENT_SOURCE_DIR}" "${STAGE01}" "${STAGE02}")
target_link_libraries(stage07_multipath_validation_lib PUBLIC
    stage07_block_core stage07_segmented_core)
target_compile_features(stage07_multipath_validation_lib PUBLIC cxx_std_17)

add_executable(stage07_multipath_validation_test stage07_multipath_validation_test.cpp)
target_link_libraries(stage07_multipath_validation_test PRIVATE stage07_multipath_validation_lib)
add_executable(stage07_multipath_validation_runner stage07_multipath_validation_runner.cpp)
target_link_libraries(stage07_multipath_validation_runner PRIVATE stage07_multipath_validation_lib)

enable_testing()
add_test(NAME stage07_multipath_validation_unit COMMAND stage07_multipath_validation_test)
