cmake_minimum_required(VERSION 2.8)

project(FunctionExtractor)

cmake_policy(SET CMP0057 NEW)

list(APPEND CMAKE_MODULE_PATH "${LLVM_DIR}")

set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wall -std=c++14 -fno-rtti")
if(APPLE)
	set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -undefined dynamic_lookup")
endif(APPLE)

find_package(LLVM REQUIRED CONFIG)
message(STATUS "Found LLVM ${LLVM_PACKAGE_VERSION}")
message(STATUS "Using LLVMConfig.cmake in: ${LLVM_DIR}")

include(AddLLVM)

find_package(Clang REQUIRED CONFIG)

message("LLVM STATUS:
    Definitions ${LLVM_DEFINITIONS}
    Includes    ${LLVM_INCLUDE_DIRS}
                ${CLANG_INCLUDE_DIRS}
    Libraries   ${LLVM_LIBRARY_DIRS}")

include_directories(${LLVM_INCLUDE_DIRS} ${CLANG_INCLUDE_DIRS})
add_definitions(${LLVM_DEFINITIONS})

add_subdirectory(FunctionExtractor)
