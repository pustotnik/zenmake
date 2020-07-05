#include <iostream>
#include "engine.h"

#ifndef HAVE_STRING
    // compiler error
    no define HAVE_STRING
#endif

#ifndef HAVE_VECTOR
    // compiler error
    no define HAVE_VECTOR
#endif

int main()
{
    std::cout << "func: main" << std::endl;
    int result = calcSomething();
    std::cout << "result: " << result << std::endl;
    return 0;
}
