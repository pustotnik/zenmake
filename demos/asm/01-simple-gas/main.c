#include <stdio.h>

int mult10(int);

int main()
{
    int asmVal = mult10(2);
    printf("From ASM: %d\n", asmVal);
    return 0;
}
