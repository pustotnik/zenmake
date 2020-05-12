#include <stdio.h>
#include "calclib/calc.h"
#include "printlib/myprint.h"

int main(int argc, char **argv) 
{
    myprint("test service");
    int a = 11;
    int b = 22;
    int rv = calcSum(a, b);
    printf("result = %d\n", rv);
    return 0;
}
