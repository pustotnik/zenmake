
#include "calc/calc.h"
#include "print/print.h"
#include "core/core.h"
#include "engine.h"

void calcSomething()
{

    int a = 11;
    int b = 22;
    int c = 33;
    
    printMsg("Hello there!");
    
    calcSumAndPrint(a, b);
    calcSumAndPrint(b, c);
    
    int sum = calcSum3(a, b, c);
    calcSumAndPrint(sum, c);
}
