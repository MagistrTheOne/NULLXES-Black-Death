cmake_minimum_required(VERSION 3.16)
project(bd_alpha_l0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Flight artifact: library only. Host smoke lives in 99_tools/host/.
add_library(bd_inner_loop
  inner_loop.cpp
)
target_include_directories(bd_inner_loop PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
