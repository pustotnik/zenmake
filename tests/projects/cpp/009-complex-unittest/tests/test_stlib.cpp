
#include <iostream>
#include "stlib/util.h"
#include "tests/common.h"

int main()
{
    std::cout << "Tests of stlib ..." << std::endl;

    if (! expectEq(calcSum(1, 3), 4)) {
        return 1;
    }

    if (! expectEq(calcSum(11, 30), 41)) {
        return 1;
    }

    return 0;
}
