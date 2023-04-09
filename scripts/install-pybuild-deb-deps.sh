#!/bin/bash

set -ex

function package_exists() {
    return apt-cache show "$1" &> /dev/null
}

INSTALL_CMD='apt-get -y --no-install-recommends install'

$INSTALL_CMD \
    build-essential libssl-dev zlib1g-dev libbz2-dev \
    libreadline-dev libsqlite3-dev wget curl llvm libncurses5-dev \
    xz-utils tk-dev libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev \
    libncursesw5-dev git ca-certificates

if package_exists python-openssl ; then
    $INSTALL_CMD python-openssl
fi

if package_exists python3-openssl ; then
    $INSTALL_CMD python3-openssl
fi