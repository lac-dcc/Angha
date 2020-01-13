add_llvm_library(FunctionExtractor SHARED FunctionExtractor.cpp)

target_link_libraries(FunctionExtractor ${llvm_libs})
