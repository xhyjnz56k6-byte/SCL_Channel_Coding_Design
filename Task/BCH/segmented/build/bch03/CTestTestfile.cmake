# CMake generated Testfile for 
# Source directory: C:/Users/V3169/Desktop/Project/SCL_Channel_Coding_Design/Task/BCH/segmented/current
# Build directory: C:/Users/V3169/Desktop/Project/SCL_Channel_Coding_Design/Task/BCH/segmented/build/bch03
# 
# This file includes the relevant testing commands required for 
# testing this directory and lists subdirectories to be tested as well.
add_test(bch15_encoder "C:/Users/V3169/Desktop/Project/SCL_Channel_Coding_Design/Task/BCH/segmented/build/bch03/test_bch15_encoder.exe" "C:/Users/V3169/Desktop/Project/SCL_Channel_Coding_Design/Task/BCH/segmented/current/../stages/bch02_bch15_encoder" "C:/Users/V3169/Desktop/Project/SCL_Channel_Coding_Design/Task/BCH/segmented/current/../config/bch15_reference_vectors.csv")
set_tests_properties(bch15_encoder PROPERTIES  _BACKTRACE_TRIPLES "C:/Users/V3169/Desktop/Project/SCL_Channel_Coding_Design/Task/BCH/segmented/current/CMakeLists.txt;9;add_test;C:/Users/V3169/Desktop/Project/SCL_Channel_Coding_Design/Task/BCH/segmented/current/CMakeLists.txt;0;")
add_test(bch15_syndrome_table "C:/Users/V3169/Desktop/Project/SCL_Channel_Coding_Design/Task/BCH/segmented/build/bch03/test_bch15_syndrome_table.exe" "C:/Users/V3169/Desktop/Project/SCL_Channel_Coding_Design/Task/BCH/segmented/current/../stages/bch03_bch15_syndrome_table")
set_tests_properties(bch15_syndrome_table PROPERTIES  _BACKTRACE_TRIPLES "C:/Users/V3169/Desktop/Project/SCL_Channel_Coding_Design/Task/BCH/segmented/current/CMakeLists.txt;12;add_test;C:/Users/V3169/Desktop/Project/SCL_Channel_Coding_Design/Task/BCH/segmented/current/CMakeLists.txt;0;")
