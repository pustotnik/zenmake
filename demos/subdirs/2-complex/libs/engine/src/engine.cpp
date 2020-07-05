#include <iostream>
#include "common.h"
#include "extra.h"
#include "engine.h"

#include "engine_config.h"

#ifndef HAVE_IOSTREAM
    // compiler error
    no define HAVE_IOSTREAM
#endif

#ifndef HAVE_STRING
    // compiler error
    no define HAVE_STRING
#endif

#ifndef HAVE_VECTOR
    // compiler error
    no define HAVE_VECTOR
#endif

int calcSomething()
{

    std::cout << "func: calcSomething" << std::endl;
    int result = calcSum3(2, 10, doubleSum(5, 10));
    return result;
}
