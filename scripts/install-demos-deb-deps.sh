#!/bin/bash

set -ex

apt-get -y --no-install-recommends install \
    make clang gcc g++ \
    bison nasm yasm gfortran gdc ldc lua5.1 \
    libboost-random-dev libboost-timer-dev \
    libdbus-glib-1-dev libgtk-3-dev libsdl2-dev \
    qt5-default qttools5-dev-tools \
