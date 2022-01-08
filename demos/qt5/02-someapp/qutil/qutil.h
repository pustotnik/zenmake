#pragma once

#include <QString>

#ifdef _MSC_VER
    #define LIB_EXPORT __declspec(dllexport)
#else
    #define LIB_EXPORT
#endif

LIB_EXPORT int calcSomething();
LIB_EXPORT QString getTranslated();
