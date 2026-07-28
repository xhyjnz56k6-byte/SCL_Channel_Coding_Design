cmake_minimum_required(VERSION 3.16)
project(stage08_multipath_formal_common_snr LANGUAGES CXX)

set(BCH_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../../../../..")
set(COMMON_ROOT "${BCH_ROOT}/../Common")
set(STAGE01 "${CMAKE_CURRENT_SOURCE_DIR}/../../stage01_foundation/cpp")
set(STAGE02 "${CMAKE_CURRENT_SOURCE_DIR}/../../stage02_case_contract/cpp")
set(STAGE07 "${CMAKE_CURRENT_SOURCE_DIR}/../../stage07_multipath_validation/cpp")

add_library(stage08_block_core "${BCH_ROOT}/block/current/src/bch_block.cpp")
target_include_directories(stage08_block_core PUBLIC
    "${BCH_ROOT}/block/current/include" "${COMMON_ROOT}/include")
target_compile_features(stage08_block_core PUBLIC cxx_std_17)

add_library(stage08_segmented_core
    "${BCH_ROOT}/segmented/current/src/bch15_encoder.cpp"
    "${BCH_ROOT}/segmented/current/src/bch15_syndrome.cpp"
    "${BCH_ROOT}/segmented/current/src/bch15_lookup_table.cpp"
    "${BCH_ROOT}/segmented/current/src/bch15_lookup_decoder.cpp"
    "${BCH_ROOT}/segmented/current/src/bch15_segmented_adapter.cpp")
target_include_directories(stage08_segmented_core PUBLIC
    "${BCH_ROOT}/segmented/current/include" "${COMMON_ROOT}/include")
target_compile_features(stage08_segmented_core PUBLIC cxx_std_17)

add_library(stage08_formal_lib
    "${STAGE01}/stage01_foundation_awgn.cpp"
    "${STAGE02}/stage02_case_contract.cpp"
    "${STAGE07}/stage07_multipath_validation_core.cpp")
target_include_directories(stage08_formal_lib PUBLIC
    "${STAGE01}" "${STAGE02}" "${STAGE07}")
target_link_libraries(stage08_formal_lib PUBLIC stage08_block_core stage08_segmented_core)
target_compile_features(stage08_formal_lib PUBLIC cxx_std_17)

add_executable(stage08_multipath_formal_common_snr_runner stage08_multipath_formal_common_snr_runner.cpp)
target_link_libraries(stage08_multipath_formal_common_snr_runner PRIVATE stage08_formal_lib)
