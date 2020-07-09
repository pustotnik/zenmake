#include <iostream>
#include "stlib/util.h"
#include "shlib/util.h"
#include "shlibmain/util.h"

int calcSomething()
{

#ifndef DOIT
    error: no define 'DOIT'
#endif

    std::cout << "func: calcSomething" << std::endl;
    std::cout << "define MY_LONG_STRING: " << MY_LONG_STRING << std::endl;
    int result = calcSum3(2, 10, calcSum(10, 20));
    return result;
}
