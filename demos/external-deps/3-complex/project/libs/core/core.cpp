
#include "calclib/calc.h"
#include "printlib/myprint.h"
#include "core.h"

void calcSumAndPrint(int a, int b)
{
    int sum = calcSum(a, b);
    
    printStr("Sum of ");
    printInt(a);
    printStr(" and ");
    printInt(b);
    printStr(" is equal to ");
    printInt(sum);
    printStr("\n");
}
