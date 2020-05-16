#include <stdio.h>
#include "calc/calc.h"
#include "print/print.h"

int main(int argc, char **argv) 
{
    printMsg("test service");
    int a = 11;
    int b = 22;
    int c = 33;
    int rv = calcSum3(a, b, c);
    printf("result = %d\n", rv);
    return 0;
}
