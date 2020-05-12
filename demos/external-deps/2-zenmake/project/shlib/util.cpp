#include <iostream>
#include "shlib/util.h"
#include "calclib/calc.h"
#include "printlib/myprint.h"

void testutil()
{
    int rv = calcSum(1,2);
    std::cout << "test passed" << std::endl;
    myprint("test util called");
}
