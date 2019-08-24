
#include <iostream>
#include <cstdlib>
#include "shlib/util.h"
#include "tests/common.h"

int main()
{
    std::cout << "Tests of shlib ..." << std::endl;

    if (! expectEq(calcSum3(1, 2, 3), 6)) {
        return 1;
    }

    if (! expectEq(calcSum3(-11, -30, 42), 1)) {
        return 1;
    }

    //if (! expectEq(calcSum3(-11, -30, 42), 2)) {
    //    return 2;
    //}

    const char* v = std::getenv("AZ");
    std::cout << "AZ = " << v << std::endl;

    return 0;
}
