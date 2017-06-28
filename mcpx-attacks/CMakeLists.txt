cmake_minimum_required(VERSION 3.7)

find_package(OpenSSL REQUIRED)

include_directories(${OPENSSL_INCLUDE_DIR})
add_executable(mcpx-attack main.c common.h tea.h)
target_link_libraries(mcpx-attack ${OPENSSL_LIBRARIES})
