#!/bin/bash

set -ex

#choco install python --version "3.7.4"
#choco install mingw
#choco install ldc

if [[ $CACHE_INDY_HIT != "true" ]]; then
    choco install boost-msvc-14.1 --version=1.74.0
fi
