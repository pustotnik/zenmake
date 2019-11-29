#include <iostream>
#include "core.h"
#include "extra.h"

int doubleSum(int a, int b)
{

    std::cout << "func: doubleSum" << std::endl;
    int result = 2 * calcSum(a, b);
    return result;
}
