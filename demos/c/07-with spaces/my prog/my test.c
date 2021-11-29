#include <stdio.h>
#include "my shlib/my util.h"

int main(int argc, char **argv)
{
    foo();
    foo2();

    if (argc > 1)
    {
        printf("The command line argument supplied is '%s'\n", argv[1]);
    }

    printf("The demo 'with spaces' has finished\n");
    return 0;
}
