#include <iostream>
#include "shlibmain/util.h"

int main()
{
    std::cout << "func: main" << std::endl;
    int result = calcSomething();
    std::cout << "result: " << result << std::endl;
    std::cout << "The program has finished" << std::endl;
    return 0;
}
