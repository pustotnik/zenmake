#ifndef __ZMDEP_PRINTLIB_MYPRINT_H__
#define __ZMDEP_PRINTLIB_MYPRINT_H__

#ifdef _MSC_VER
    #define LIB_EXPORT __declspec(dllexport)
#else
    #define LIB_EXPORT
#endif

#ifdef __cplusplus
extern "C" {
#endif

LIB_EXPORT void myprint(const char* msg);

#ifdef __cplusplus
}
#endif

#endif
