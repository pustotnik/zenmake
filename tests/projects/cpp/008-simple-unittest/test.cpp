#include <iostream>
#include "util.h"

/*
It's not necessary to use real testing framework like gtest, boost.test,
catch2, etc to check/test building and running of tests. So here is some
primitive emulation.
*/

bool expectEq(unsigned n1, unsigned n2) {
    if (n1 != n2) {
        std::cout << n1 << " is not equal to " << n2 << std::endl;
        return false;
    }

    return true;
}

int main()
{
    unsigned n = 6;
    if (! expectEq(factorial(n), 720)) {
        return 1;
    }

    return 0;
}
