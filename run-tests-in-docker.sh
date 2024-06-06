#!/bin/bash

set -e

# detect right directory and go into it
cd "$( dirname "$(realpath ${BASH_SOURCE[0]:-$0})" )/docker"

DISTRO=${DISTRO:-debian}

#./run-tests.sh ubuntu
#./run-tests.sh debian "system 3.9"

args=("$@")
./run-tests.sh "${DISTRO}" "${args[*]}"
