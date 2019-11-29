#include <iostream>
#include "core.h"

int calcSum(int a, int b)
{
    std::cout << "func: calcSum" << std::endl;
    return a + b;
}

int calcSum3(int a, int b, int c)
{
    std::cout << "func: calcSum3" << std::endl;
    return a + b + c;
}
