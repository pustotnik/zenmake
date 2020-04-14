#ifndef __ZENMAKE_TEST_C_UTIL_H__
#define __ZENMAKE_TEST_C_UTIL_H__

#ifdef _MSC_VER
    #define LIB_EXPORT __declspec(dllexport)
#else
    #define LIB_EXPORT
#endif

#ifdef __cplusplus
extern "C" {
#endif

LIB_EXPORT void foo();

#ifdef __cplusplus
}
#endif

#endif
