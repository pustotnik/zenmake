
#include <iostream>
#include <cstdlib>
#include <string>
#include "extra.h"
#include "test_common.h"

int main()
{
    std::cout << "Tests of lib 'extra'..." << std::endl;

    const char* envAZ = std::getenv("AZ");
    std::string strAZ = "NULL";
    if (envAZ) 
    { 
        strAZ = envAZ;
    }
    
    const char* envBrokenTest = std::getenv("BROKEN_TEST");
    std::string strBrokenTest = "NULL";
    if (envBrokenTest) 
    { 
        strBrokenTest = envBrokenTest;
    }
    
    std::cout << "env var 'AZ' = " << strAZ << std::endl;
    std::cout << "env var 'BROKEN_TEST' = " << strBrokenTest << std::endl;

    if (! expectEq(doubleSum(1, 2), 6))
    {
        return 1;
    }

    if (strBrokenTest == "true")
    {
        if (! expectEq(doubleSum(1, 2), 7)) {
            return 2;
        }
    }

    return 0;
}
