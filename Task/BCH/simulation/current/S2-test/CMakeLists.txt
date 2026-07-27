add_library(bch_s2_multipath
    src/bch_multipath_simulation.cpp
    src/fixed_multipath_mmse.cpp)
target_include_directories(bch_s2_multipath PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/include
    ${CMAKE_CURRENT_SOURCE_DIR}/../include)
target_link_libraries(bch_s2_multipath PUBLIC bch_case_adapter common_bch_simulation)
target_compile_features(bch_s2_multipath PUBLIC cxx_std_17)

add_executable(test_bch_s2_mmse tests/test_bch_s2_mmse.cpp)
target_link_libraries(test_bch_s2_mmse PRIVATE bch_s2_multipath)

add_executable(bch_multipath_runner src/bch_multipath_runner.cpp)
target_link_libraries(bch_multipath_runner PRIVATE bch_s2_multipath)

add_executable(export_bch_s2_matlab_vectors tests/export_bch_s2_matlab_vectors.cpp)
target_link_libraries(export_bch_s2_matlab_vectors PRIVATE bch_s2_multipath)

add_test(NAME bch_s2_mmse_unit COMMAND test_bch_s2_mmse)
