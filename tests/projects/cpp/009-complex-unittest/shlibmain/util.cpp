#include <iostream>
#include "stlib/util.h"
#include "shlib/util.h"
#include "shlibmain/util.h"

int calcSomething()
{
    std::cout << "func: calcSomething" << std::endl;
    int result = calcSum3(2, 10, calcSum(10, 20));
    return result;
}
