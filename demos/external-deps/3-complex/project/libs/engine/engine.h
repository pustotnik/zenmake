#ifndef __ZENMAKE_EDEPS_COMPLEX_ENGINE_H__
#define __ZENMAKE_EDEPS_COMPLEX_ENGINE_H__

#ifdef _MSC_VER
    #define LIB_EXPORT __declspec(dllexport)
#else
    #define LIB_EXPORT
#endif

LIB_EXPORT void calcSomething();

#endif
