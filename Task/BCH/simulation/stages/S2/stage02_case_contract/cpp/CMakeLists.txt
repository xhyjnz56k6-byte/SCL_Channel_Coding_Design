cmake_minimum_required(VERSION 3.16)
project(stage02_case_contract LANGUAGES CXX)

set(BCH_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../../../../..")
set(COMMON_ROOT "${BCH_ROOT}/../Common")

add_library(stage02_block_core
    "${BCH_ROOT}/block/current/src/bch_block.cpp")
target_include_directories(stage02_block_core PUBLIC
    "${BCH_ROOT}/block/current/include"
    "${COMMON_ROOT}/include")
target_compile_features(stage02_block_core PUBLIC cxx_std_17)

add_library(stage02_segmented_core
    "${BCH_ROOT}/segmented/current/src/bch15_encoder.cpp"
    "${BCH_ROOT}/segmented/current/src/bch15_syndrome.cpp"
    "${BCH_ROOT}/segmented/current/src/bch15_lookup_table.cpp"
    "${BCH_ROOT}/segmented/current/src/bch15_lookup_decoder.cpp"
    "${BCH_ROOT}/segmented/current/src/bch15_segmented_adapter.cpp")
target_include_directories(stage02_segmented_core PUBLIC
    "${BCH_ROOT}/segmented/current/include"
    "${COMMON_ROOT}/include")
target_compile_features(stage02_segmented_core PUBLIC cxx_std_17)

add_library(stage02_case_contract_lib
    stage02_case_contract.cpp)
target_include_directories(stage02_case_contract_lib PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
target_link_libraries(stage02_case_contract_lib PUBLIC stage02_block_core stage02_segmented_core)
target_compile_features(stage02_case_contract_lib PUBLIC cxx_std_17)

add_executable(stage02_case_contract_test stage02_case_contract_test.cpp)
target_link_libraries(stage02_case_contract_test PRIVATE stage02_case_contract_lib)
add_executable(stage02_case_contract_export stage02_case_contract_export.cpp)
target_link_libraries(stage02_case_contract_export PRIVATE stage02_case_contract_lib)

enable_testing()
add_test(NAME stage02_case_contract_unit COMMAND stage02_case_contract_test)
