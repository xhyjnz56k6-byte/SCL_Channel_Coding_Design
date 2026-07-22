cmake_minimum_required(VERSION 3.16)
project(Bch15Encoder LANGUAGES CXX)
add_library(bch15_encoder src/bch15_encoder.cpp src/bch15_syndrome.cpp src/bch15_lookup_table.cpp src/bch15_lookup_decoder.cpp src/bch15_segmented_adapter.cpp)
target_include_directories(bch15_encoder PUBLIC include ../../../Common/include)
target_compile_features(bch15_encoder PUBLIC cxx_std_17)
set(BCH_TEST_OUTPUT_ROOT ${CMAKE_CURRENT_BINARY_DIR}/test_outputs)
file(MAKE_DIRECTORY
    ${BCH_TEST_OUTPUT_ROOT}/bch02_encoder
    ${BCH_TEST_OUTPUT_ROOT}/bch03_syndrome_table
    ${BCH_TEST_OUTPUT_ROOT}/bch04_lookup_decoder
    ${BCH_TEST_OUTPUT_ROOT}/bch05_segmented_adapter
)
add_executable(test_bch15_encoder tests/test_bch15_encoder.cpp)
target_link_libraries(test_bch15_encoder PRIVATE bch15_encoder)
enable_testing()
add_test(NAME bch15_encoder COMMAND test_bch15_encoder ${BCH_TEST_OUTPUT_ROOT}/bch02_encoder ${CMAKE_CURRENT_SOURCE_DIR}/../config/bch15_reference_vectors.csv)
add_executable(test_bch15_syndrome_table tests/test_bch15_syndrome_table.cpp)
target_link_libraries(test_bch15_syndrome_table PRIVATE bch15_encoder)
add_test(NAME bch15_syndrome_table COMMAND test_bch15_syndrome_table ${BCH_TEST_OUTPUT_ROOT}/bch03_syndrome_table)
add_executable(test_bch15_lookup_decoder tests/test_bch15_lookup_decoder.cpp)
target_link_libraries(test_bch15_lookup_decoder PRIVATE bch15_encoder)
add_test(NAME bch15_lookup_decoder COMMAND test_bch15_lookup_decoder ${BCH_TEST_OUTPUT_ROOT}/bch04_lookup_decoder ${CMAKE_CURRENT_SOURCE_DIR}/../config/bch15_multi_error_seeds.csv)
add_executable(test_bch15_segmented_adapter tests/test_bch15_segmented_adapter.cpp)
target_link_libraries(test_bch15_segmented_adapter PRIVATE bch15_encoder)
add_test(NAME bch15_segmented_adapter COMMAND test_bch15_segmented_adapter ${BCH_TEST_OUTPUT_ROOT}/bch05_segmented_adapter ${CMAKE_CURRENT_SOURCE_DIR}/../../../Common/build/stage04/real_pool_runs/smoke/frames/k200/manifest.json ${CMAKE_CURRENT_SOURCE_DIR}/../../../Common/build/stage04/real_pool_runs/smoke/frames/k300/manifest.json)
