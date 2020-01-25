#include <iostream>
#include <cmath>

#include <boost/random/mersenne_twister.hpp>
#include <boost/random/uniform_int_distribution.hpp>

#include <boost/timer/timer.hpp>

#include "shlib/util.h"


void foo()
{
    boost::random::mt19937 rng;

    boost::random::uniform_int_distribution<> six(1,6);

    int x = six(rng);

    boost::timer::auto_cpu_timer t;

    for (long i = 0; i < 100000000; ++i)
        std::sqrt(123.456L); // burn some time

    std::cout << "test passed, x = " << x << std::endl;
}
