#ifndef __ZENMAKE_TEST_CORE_CORE_H__
#define __ZENMAKE_TEST_CORE_CORE_H__

#ifdef _MSC_VER
    #define LIB_EXPORT __declspec(dllexport)
#else
    #define LIB_EXPORT
#endif

LIB_EXPORT int calcSum(int a, int b);
LIB_EXPORT int calcSum3(int a, int b, int c);

#endif
