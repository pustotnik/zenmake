#ifndef __ZENMAKE_TEST_CPP_SHLIB_UTIL_H__
#define __ZENMAKE_TEST_CPP_SHLIB_UTIL_H__

#ifdef _MSC_VER
    #define LIB_EXPORT __declspec(dllexport)
#else
    #define LIB_EXPORT
#endif

LIB_EXPORT int calcSum3(int a, int b, int c);

#endif
