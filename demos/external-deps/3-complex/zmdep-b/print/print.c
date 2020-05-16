#include "printlib/myprint.h"
#include "print/print.h"

void printMsg(const char* msg)
{
    printStr(msg);
    printStr("\n");
}
