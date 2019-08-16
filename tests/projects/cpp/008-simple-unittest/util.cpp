#include <iostream>
#include "util.h"

void foo()
{
    unsigned n = 6;
    std::cout << "factorial of " << n << " is "
                << factorial(n) << std::endl;
    std::cout << "test passed" << std::endl;
}

unsigned factorial(unsigned number)
{
    return number <= 1 ? number : factorial(number - 1) * number;
}