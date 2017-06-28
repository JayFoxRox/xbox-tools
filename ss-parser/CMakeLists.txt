cmake_minimum_required(VERSION 3.7)

find_package(OpenSSL REQUIRED)

include_directories(${OPENSSL_INCLUDE_DIR})
add_executable(ss-parser main.c)
target_link_libraries(ss-parser ${OPENSSL_LIBRARIES})
