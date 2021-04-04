#include <stdio.h>
#include "shlib/util.h"

void foo()
{

    #ifdef WE_HAVE_STDLIB
        printf("WE_HAVE_STDLIB\n");
    #else
        err
    #endif

    #ifdef HAVE_STDIO_H
        printf("HAVE_STDIO_H\n");
    #else
        err
    #endif

    printf("test passed\n");
}
