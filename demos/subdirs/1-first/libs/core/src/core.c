#include <stdio.h>
#include "core.h"

int calcSum(int a, int b)
{
    printf("func: calcSum\n");
    return a + b;
}

int calcSum3(int a, int b, int c)
{
    printf("func: calcSum3\n");
    return a + b + c;
}
