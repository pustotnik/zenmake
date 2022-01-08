#pragma once

#ifdef _MSC_VER
    #define LIB_EXPORT __declspec(dllexport)
#else
    #define LIB_EXPORT
#endif

LIB_EXPORT int calcSum(int a, int b);
