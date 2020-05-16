#include <stdio.h>
#include "calclib/calc.h"
#include "printlib/myprint.h"

void printStr(const char* msg) 
{ 
    int d = calcSum(1,2);
    printf("%s", msg);
}

void printInt(int n) 
{ 
    printf("%d", n);
}
