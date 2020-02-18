import core.stdc.stdio;

extern (C) int testdll()
{
    printf("dll()\n");
    return 0;
}

