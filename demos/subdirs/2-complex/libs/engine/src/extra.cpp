#include <iostream>
#include "common.h"
#include "extra.h"

#include "extra_config.h"

#ifndef HAVE_IOSTREAM
    // compiler error
    no define HAVE_IOSTREAM
#endif

int doubleSum(int a, int b)
{

    std::cout << "func: doubleSum" << std::endl;
    int result = 2 * calcSum(a, b);
    return result;
}
