import core.stdc.stdio;
import dll;
import static_lib;

int main()
{
    printf("+main()\n");
    dll.testdll();
    static_lib.teststatic();
    printf("-main()\n");
    return 0;
}
