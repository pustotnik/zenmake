#ifndef __ZMDEP_A_CALCLIB_CALC_H__
#define __ZMDEP_A_CALCLIB_CALC_H__

#ifdef _MSC_VER
    #define LIB_EXPORT __declspec(dllexport)
#else
    #define LIB_EXPORT
#endif

#ifdef __cplusplus
extern "C" {
#endif

LIB_EXPORT int calcSum(int a, int b);

#ifdef __cplusplus
}
#endif

#endif
