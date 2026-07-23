cmake_minimum_required(VERSION 3.16)
project(Bch16vMatlabOfficialValidation LANGUAGES CXX)

add_subdirectory("${CMAKE_CURRENT_SOURCE_DIR}/../current" bch_group4_current)

add_executable(bch16v_export_shared_input
    cpp/bch16v_export_shared_input.cpp)
target_link_libraries(bch16v_export_shared_input PRIVATE bch_case_adapter)
target_compile_features(bch16v_export_shared_input PRIVATE cxx_std_17)

