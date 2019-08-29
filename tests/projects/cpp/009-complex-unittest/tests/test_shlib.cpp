
#include <iostream>
#include <cstdlib>
#include <string>
#include "shlib/util.h"
#include "tests/common.h"

int main()
{
    std::cout << "Tests of shlib ..." << std::endl;

    const char* envAZ = std::getenv("AZ");
    const char* envBrokenTest = std::getenv("BROKEN_TEST");
    std::cout << "env var 'AZ' = " << envAZ << std::endl;
    std::cout << "env var 'BROKEN_TEST' = " << envBrokenTest << std::endl;

    if (! expectEq(calcSum3(1, 2, 3), 6))
    {
        return 1;
    }

    if (! expectEq(calcSum3(-11, -30, 42), 1))
    {
        return 1;
    }

    std::string strBrokenTest(envBrokenTest);
    if (strBrokenTest == "true")
    {
        if (! expectEq(calcSum3(-11, -30, 42), 2)) {
            return 2;
        }
    }

    return 0;
}
