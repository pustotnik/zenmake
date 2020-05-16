
#include "calclib/calc.h"
#include "calc/calc.h"

int calcSum3(int a, int b, int c)
{
    return calcSum(calcSum(a, b), c);
}
