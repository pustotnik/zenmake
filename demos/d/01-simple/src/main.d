import std.stdio;

template Integer(int nbits)
{
    static if (nbits <= 8)
        alias Integer = byte;
    else static if (nbits <= 16)
        alias Integer = short;
    else static if (nbits <= 32)
        alias Integer = int;
    else static if (nbits <= 64)
        alias Integer = long;
    else
        static assert(0);
}

int main()
{
    Integer!(8) i ;
    Integer!(16) j ;
    Integer!(29) k ;
    Integer!(64) l ;
    writefln("%d %d %d %d", i.sizeof, j.sizeof, k.sizeof, l.sizeof);
    return 0;
}
