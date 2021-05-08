#!/bin/bash

# detect right directory and go into it
cd "$( dirname "$(realpath ${BASH_SOURCE[0]:-$0})" )/docker"

#./run-tests.sh ubuntu
./run-tests.sh debian
#./run-tests.sh debian "system 3.5"

