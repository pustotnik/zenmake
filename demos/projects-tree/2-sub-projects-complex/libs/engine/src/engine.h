#ifndef __ZENMAKE_TEST_ENGINE_ENGINE_H__
#define __ZENMAKE_TEST_ENGINE_ENGINE_H__

#ifdef _MSC_VER
    #define LIB_EXPORT __declspec(dllexport)
#else
    #define LIB_EXPORT
#endif

LIB_EXPORT int calcSomething();

#endif
