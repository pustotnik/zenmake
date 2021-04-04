#include <cstdio>
#include "shlib/util.h"
#include "testprg_config.h"

int main()
{
    #ifdef MYDEFINE
        printf("MYDEFINE\n");
    #else
        err
    #endif

    #ifdef HAVE_CSTDIO
        printf("HAVE_CSTDIO\n");
    #else
        err
    #endif

    #ifdef HAVE_IOSTREAM
        printf("HAVE_IOSTREAM\n");
    #else
        err
    #endif

    foo();
    return 0;
}
