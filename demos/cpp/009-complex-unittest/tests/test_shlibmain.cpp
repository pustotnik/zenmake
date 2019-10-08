
#include <iostream>
#include "shlibmain/util.h"
#include "tests/common.h"

int main()
{
    std::cout << "Tests of shlibmain ..." << std::endl;

    if (! expectEq(calcSomething(), 42)) {
        return 1;
    }

    return 0;
}
