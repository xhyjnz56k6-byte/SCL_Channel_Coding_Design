cmake_minimum_required(VERSION 3.16)

project(CommonFoundation LANGUAGES CXX)

add_library(common_foundation INTERFACE)
target_include_directories(common_foundation INTERFACE ${CMAKE_CURRENT_SOURCE_DIR}/include)
target_compile_features(common_foundation INTERFACE cxx_std_17)

add_executable(common02_types_interfaces_tests tests/stage02/test_common02_types_interfaces.cpp)
target_link_libraries(common02_types_interfaces_tests PRIVATE common_foundation)

set(COMMON04_SOURCES
    src/random_policy.cpp
    src/gaussian_noise.cpp
    src/noise_pool.cpp
    src/modulation.cpp
    src/awgn_channel.cpp
    src/demodulation.cpp
    src/simulation_metrics.cpp
    src/simulation_control.cpp
    src/checkpoint.cpp
    src/result_schema.cpp
    src/simulation_pipeline.cpp
)

foreach(test_name
        test_common04_random_policy
        test_common04_gaussian_noise
        test_common04_modulation_awgn
        test_common04_metrics_control
        test_common04_checkpoint
        test_common04_integration)
    add_executable(${test_name} tests/stage04/${test_name}.cpp ${COMMON04_SOURCES})
    target_link_libraries(${test_name} PRIVATE common_foundation)
endforeach()
