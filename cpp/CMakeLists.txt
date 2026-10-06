cmake_minimum_required(VERSION 3.20)
project(polarislink VERSION 2.6.1 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Header-only library interface
add_library(polarislink INTERFACE)
add_library(polarislink::polarislink ALIAS polarislink)

target_include_directories(polarislink INTERFACE
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
    $<INSTALL_INTERFACE:include>
)

# Optional libcurl linkage if found
find_package(CURL QUIET)
if(CURL_FOUND)
    target_link_libraries(polarislink INTERFACE CURL::libcurl)
endif()

# Installation rules
include(GNUInstallDirs)
install(DIRECTORY include/polarislink
    DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}
)

# Tests
option(POLARISLINK_BUILD_TESTS "Build PolarisLink C++ test suite" ON)
if(POLARISLINK_BUILD_TESTS)
    enable_testing()
    add_executable(test_polarislink tests/test_header.cpp)
    target_link_libraries(test_polarislink PRIVATE polarislink::polarislink)
    add_test(NAME polarislink_header_test COMMAND test_polarislink)
endif()
