#!/bin/bash

set -ex

dnf --nodocs -y --enablerepo=powertools install \
    make gcc clang libasan \
    bison nasm yasm lua gcc-gfortran \
    boost-random boost-timer boost-devel \
    dbus-glib-devel gtk3-devel SDL2-devel \
    qt5-qtbase-devel qt5-linguist
